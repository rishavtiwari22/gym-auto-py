import os
import json
import datetime
import time
from typing import Optional, Dict, List, Any
import gspread

class DatabaseManager:
    """
    Manages gym data storage using Google Sheets as the primary database.
    Optimized for scalability (1000+ users) with memory caching and atomic updates.
    """

    def __init__(self):
        """Initialize the manager and load initial data from Sheets."""
        self.data: Dict[str, Any] = {"members": [], "workouts": [], "classes": []}
        self.spreadsheet = None
        self.members_sheet = None
        self.payment_history_sheet = None
        self.attendance_sheet = None
        self.classes_sheet = None
        self.dashboard_sheet = None
        
        # Cache management
        self._last_data_refresh = 0
        self._refresh_interval = 300 # Refresh data cache every 5 minutes
        self._last_info_refresh = 0
        self._info_cache = {}
        
        self.use_sheets = os.getenv("ENABLE_SHEETS", "true").lower() == "true"
        
        if self.use_sheets:
            self._init_sheets_oauth()
            # We don't force refresh in __init__ to avoid timeouts on Vercel (cold starts)
            # data will be loaded on first access if needed

    def _init_sheets_oauth(self) -> None:
        """Initialize Google Sheets connection."""
        try:
            # First check for Service Account JSON in environment (Vercel/Production)
            service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
            if service_account_json:
                try:
                    creds_dict = json.loads(service_account_json)
                    gc = gspread.service_account_from_dict(creds_dict)
                except json.JSONDecodeError:
                    # If it's not JSON, it might be a path to a file (fallback)
                    gc = gspread.service_account(filename=service_account_json)
            else:
                # Fallback to OAuth flow (Local/Dev)
                gc = gspread.oauth(credentials_filename="credentials.json")
            sheet_name = os.getenv("GOOGLE_SHEET_NAME", "GymAutomationDB")
            self.spreadsheet = gc.open(sheet_name)
            
            # Data Sheets
            self.members_sheet = self._get_or_create_sheet("Members")
            self.payment_history_sheet = self._get_or_create_sheet("Payment_History")
            self.attendance_sheet = self._get_or_create_sheet("Attendance")  # Use existing sheet
            self.classes_sheet = self._get_or_create_sheet("Classes")
            self.dashboard_sheet = self._get_or_create_sheet("Analytics_Dashboard")
            
            # Config Sheets
            self.settings_sheet = self._get_or_create_sheet("General_Settings")
            self.fees_structure_sheet = self._get_or_create_sheet("Fees_Structure")
            self.trainers_info_sheet = self._get_or_create_sheet("Trainers")
            self.kb_sheet = self._get_or_create_sheet("Knowledge_Base")
            self.faq_sheet = self._get_or_create_sheet("FAQ")
            self.machines_sheet = self._get_or_create_sheet("Machines")
            
            print(f"✅ Google Sheets '{sheet_name}' initialized as Primary DB.")
        except Exception as e:
            print(f"⚠️ Google Sheets Init Error: {e}")

    def _get_or_create_sheet(self, name: str):
        """Get worksheet or create if missing."""
        try:
            return self.spreadsheet.worksheet(name)
        except gspread.exceptions.WorksheetNotFound:
            headers = {
                "Members": ["User ID", "Full Name", "Phone", "Address", "Occupation", "Plan", "Membership Type", "Duration (Months)", "Amount Paid", "Status", "Join Date", "Expiry Date", "Last Renewal"],
                "Payment_History": ["Transaction ID", "User ID", "Full Name", "Date", "Action", "Plan", "Duration (Months)", "Amount", "Expiry Date", "Payment Method", "Due Date", "Due Amount"],
                "Attendance": ["Session ID", "User ID", "Full Name", "Date", "Check-In Time", "Check-Out Time", "Duration (mins)", "Notes"],
                "Classes": ["Class ID", "Class Name", "Day", "Time", "Duration", "Instructor", "Max Capacity", "Current Enrolled", "Availability", "Active"],
                "Machines": ["Machine Name", "Muscles Trained", "Description", "Active"]
            }
            sheet = self.spreadsheet.add_worksheet(title=name, rows=2000, cols=20)
            if name in headers:
                sheet.update(values=[headers[name]], range_name="A1")
            return sheet

    def refresh_cache(self, force: bool = False) -> None:
        """Refresh local memory cache from Sheets."""
        now = time.time()
        if not force and (now - self._last_data_refresh < self._refresh_interval):
            return

        try:
            print("🔄 Refreshing Cache from Google Sheets...")
            if self.members_sheet:
                self.data["members"] = self.members_sheet.get_all_records()
            if self.attendance_sheet:
                # Load last 1000 logs for performance
                all_logs = self.attendance_sheet.get_all_records()
                self.data["workouts"] = all_logs[-1000:]
            if self.classes_sheet:
                self.data["classes"] = self.classes_sheet.get_all_records()
            if self.machines_sheet:
                self.data["machines"] = self.machines_sheet.get_all_records()
            
            self._last_data_refresh = now
            print(f"✅ Cache Updated. Members: {len(self.data['members'])}")
        except Exception as e:
            print(f"⚠️ Cache Refresh Failed: {e}")

    # --- Member Methods ---
    def get_member(self, user_id: Any) -> Optional[Dict[str, Any]]:
        self.refresh_cache()
        for m in self.data["members"]:
            if str(m.get("User ID")) == str(user_id):
                return m
        return None

    def add_member(self, user_id: Any, full_name: str, plan: str, phone: str = "", 
                   status: str = "Active", address: str = "", occupation: str = "", 
                   amount_paid: str = "0", duration_months: int = 1,
                   membership_type: str = "Regular", due_date: str = "", due_amount: str = "0") -> Dict[str, Any]:
        now = datetime.datetime.now()
        join_date = now.strftime("%Y-%m-%d")
        
        if membership_type == "Trial":
            expiry_date = (now + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        else:
            expiry_date = (now + datetime.timedelta(days=30 * duration_months)).strftime("%Y-%m-%d")
        
        member_row = [
            str(user_id), full_name, phone, address, occupation, plan,
            membership_type, duration_months if membership_type != "Trial" else 0,
            amount_paid, status, join_date, expiry_date, join_date  # 13 columns - removed due_date, due_amount
        ]
        
        # 1. Update Sheets (Member row)
        existing_member = self.get_member(user_id)
        if existing_member:
            # Optimize: Use memory cache to find row index instead of slow col_values() API call
            row_idx = -1
            for i, m in enumerate(self.data.get("members", [])):
                if str(m.get("User ID")) == str(user_id):
                    row_idx = i + 2 # +1 for 1-indexing, +1 for headers
                    break
            
            if row_idx != -1:
                self.members_sheet.update(values=[member_row], range_name=f"A{row_idx}:M{row_idx}")
            else:
                self.members_sheet.append_row(member_row)
        else:
            self.members_sheet.append_row(member_row)

        # 2. Add to Payment History
        txn_id = f"TXN_{user_id}_{now.strftime('%Y%m%d%H%M')}"
        payment_row = [
            txn_id, str(user_id), full_name, join_date, 
            "Joined" if membership_type == "Regular" else "Trial Booked",
            plan, duration_months, amount_paid, expiry_date, "UPI/Cash", "New Member"
        ]
        self.payment_history_sheet.append_row(payment_row)
        
        # 3. Force refresh cache to include new member
        self.refresh_cache(force=True)
        return self.get_member(user_id)

    def update_member_status(self, user_id: Any, status: str) -> bool:
        members = self.members_sheet.col_values(1)
        try:
            row_idx = members.index(str(user_id)) + 1
            self.members_sheet.update_cell(row_idx, 10, status) # Column J is Status
            self.refresh_cache(force=True)
            return True
        except ValueError:
            return False

    def delete_member(self, user_id: Any) -> bool:
        members = self.members_sheet.col_values(1)
        try:
            row_idx = members.index(str(user_id)) + 1
            self.members_sheet.delete_rows(row_idx)
            self.refresh_cache(force=True)
            return True
        except ValueError:
            return False

    # --- Workout/Attendance ---
    def log_workout(self, user_id: Any, workout_type: str, duration: str, notes: str = "") -> Dict[str, Any]:
        now = datetime.datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")
        member = self.get_member(user_id)
        name = member.get("Full Name", "Unknown") if member else "Unknown"
        
        log_id = f"LOG_{user_id}_{now.strftime('%Y%m%d%H%M')}"
        row = [log_id, date_str, time_str, str(user_id), name, workout_type, duration, notes, True]
        
        self.attendance_sheet.append_row(row)
        self.refresh_cache(force=True)
        return {"Timestamp": f"{date_str} {time_str}", "User ID": user_id, "Workout Type": workout_type}

    def get_member_workouts(self, user_id: Any, limit: int = 5) -> List[Dict[str, Any]]:
        self.refresh_cache()
        user_workouts = [w for w in self.data["workouts"] if str(w.get("User ID")) == str(user_id)]
        return user_workouts[-limit:][::-1] # Last N, newest first

    # --- Classes ---
    def get_classes(self) -> List[Dict[str, Any]]:
        self.refresh_cache()
        return self.data.get("classes", [])

    def update_class(self, class_name: str, time: str, instructor: str, availability: str) -> bool:
        classes = self.classes_sheet.col_values(2) # Class Name is Col B
        try:
            row_idx = classes.index(class_name) + 1
            self.classes_sheet.update(values=[[time, instructor, availability]], range_name=f"D{row_idx}:F{row_idx}")
        except ValueError:
            new_id = f"CLS_{len(classes)}"
            self.classes_sheet.append_row([new_id, class_name, "Mon-Sat", time, "60m", instructor, 20, 0, availability, True])
        
        self.refresh_cache(force=True)
        return True

    # --- Analytics & Reports ---
    def get_all_members(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        self.refresh_cache()
        m_list = self.data["members"]
        if status:
            return [m for m in m_list if m.get("Status") == status]
        return m_list

    def get_revenue_stats(self) -> Dict[str, Any]:
        self.refresh_cache()
        history = self.payment_history_sheet.get_all_records()
        now = datetime.datetime.now()
        current_month = now.strftime("%Y-%m")
        total = 0
        monthly = 0
        new_members_count = 0
        
        # Count members joined this month
        for m in self.data["members"]:
            join_date = m.get("Join Date", "")
            if join_date.startswith(current_month):
                new_members_count += 1

        for entry in history:
            amt_str = str(entry.get("Amount", "0")).replace("₹", "").replace(",", "").strip()
            try:
                amt = float(amt_str) if amt_str else 0.0
            except ValueError:
                amt = 0.0
            total += amt
            if str(entry.get("Date", "")).startswith(current_month):
                monthly += amt
                
        return {
            "total": total, 
            "monthly": monthly, 
            "month_display": now.strftime("%B %Y"),
            "new_members": new_members_count
        }

    def get_recent_transactions(self, limit: int = 5) -> List[Dict[str, Any]]:
        history = self.payment_history_sheet.get_all_records()
        return history[-limit:][::-1]

    def get_dues_report(self) -> List[Dict[str, Any]]:
        self.refresh_cache()
        return [m for m in self.data["members"] if m.get("Status") == "Pending"]

    def get_expiring_soon(self, days: int = 7) -> List[Dict[str, Any]]:
        self.refresh_cache()
        soon = []
        now = datetime.datetime.now()
        for m in self.data["members"]:
            try:
                exp_str = m.get("Expiry Date")
                if not exp_str: continue
                exp = datetime.datetime.strptime(exp_str, "%Y-%m-%d")
                days_left = (exp - now).days
                if 0 <= days_left <= days:
                    m_copy = m.copy()
                    m_copy["days_left"] = days_left
                    soon.append(m_copy)
            except: pass
        return soon

    def get_expired_members(self) -> List[Dict[str, Any]]:
        self.refresh_cache()
        expired = []
        now = datetime.datetime.now()
        for m in self.data["members"]:
            try:
                exp_str = m.get("Expiry Date")
                if not exp_str: continue
                exp = datetime.datetime.strptime(exp_str, "%Y-%m-%d")
                if exp < now:
                    m_copy = m.copy()
                    m_copy["days_expired"] = (now - exp).days
                    expired.append(m_copy)
            except: pass
        return expired

    def get_retention_risk(self, days: int = 7) -> List[Dict[str, Any]]:
        """Members with no workout in last X days."""
        self.refresh_cache()
        risk = []
        now = datetime.datetime.now()
        
        # 1. Map each user to their LAST workout date
        last_workouts = {}
        for w in self.data["workouts"]:
            uid = str(w.get("User ID"))
            try:
                w_date = datetime.datetime.strptime(w.get("Date"), "%Y-%m-%d")
                if uid not in last_workouts or w_date > last_workouts[uid]:
                    last_workouts[uid] = w_date
            except: continue

        # 2. Compare against active members
        for m in self.data["members"]:
            if m.get("Status") != "Active": continue
            
            uid = str(m.get("User ID"))
            last_date = last_workouts.get(uid)
            
            if not last_date:
                # Never worked out - check join date
                try:
                    join_date = datetime.datetime.strptime(m.get("Join Date"), "%Y-%m-%d")
                    inactive_days = (now - join_date).days
                except: inactive_days = 99
            else:
                inactive_days = (now - last_date).days

            if inactive_days >= days:
                m_copy = m.copy()
                m_copy["inactive_days"] = inactive_days
                risk.append(m_copy)
        
        return sorted(risk, key=lambda x: x["inactive_days"], reverse=True)

    def get_daily_attendance(self, date_str: Optional[str] = None) -> List[Dict[str, Any]]:
        self.refresh_cache()
        if not date_str:
            date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        return [w for w in self.data["workouts"] if w.get("Date") == date_str]

    def get_top_active_members(self, limit: int = 10) -> List[Dict[str, Any]]:
        self.refresh_cache()
        counts = {}
        for w in self.data["workouts"]:
            uid = str(w.get("User ID"))
            counts[uid] = counts.get(uid, 0) + 1
        
        sorted_uids = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:limit]
        top_members = []
        for uid, count in sorted_uids:
            member = self.get_member(uid)
            if member:
                member_copy = member.copy()
                member_copy["workout_count"] = count
                top_members.append(member_copy)
        return top_members

    def get_growth_stats(self) -> Dict[str, Any]:
        self.refresh_cache()
        history = self.payment_history_sheet.get_all_records()
        now = datetime.datetime.now()
        current_month_str = now.strftime("%Y-%m")
        last_month = now.replace(day=1) - datetime.timedelta(days=1)
        last_month_str = last_month.strftime("%Y-%m")
        
        this_month_rev = 0
        last_month_rev = 0
        this_month_members = 0
        last_month_members = 0

        for entry in history:
            amt_str = str(entry.get("Amount", "0")).replace("₹", "").replace(",", "").strip()
            try:
                amt = float(amt_str) if amt_str else 0.0
            except ValueError:
                amt = 0.0
            date_str = str(entry.get("Date", ""))
            if date_str.startswith(current_month_str):
                this_month_rev += amt
            elif date_str.startswith(last_month_str):
                last_month_rev += amt

        for m in self.data["members"]:
            join_date = m.get("Join Date", "")
            if join_date.startswith(current_month_str):
                this_month_members += 1
            elif join_date.startswith(last_month_str):
                last_month_members += 1

        rev_growth = ((this_month_rev - last_month_rev) / last_month_rev * 100) if last_month_rev > 0 else 100
        mem_growth = ((this_month_members - last_month_members) / last_month_members * 100) if last_month_members > 0 else 100

        return {
            "month_name": now.strftime("%B"),
            "rev_growth": f"{'+' if rev_growth >= 0 else ''}{rev_growth:.1f}%",
            "member_growth": f"{'+' if mem_growth >= 0 else ''}{mem_growth:.1f}%",
            "this_month": {"revenue": this_month_rev, "members": this_month_members},
            "last_month": {"revenue": last_month_rev, "members": last_month_members}
        }

    def get_occupation_breakdown(self) -> Dict[str, int]:
        self.refresh_cache()
        counts = {}
        for m in self.data["members"]:
            occ = m.get("Occupation", "Other")
            counts[occ] = counts.get(occ, 0) + 1
        return counts

    def search_members(self, query: str) -> List[Dict[str, Any]]:
        self.refresh_cache()
        q = query.lower()
        return [m for m in self.data["members"] if q in m.get("Full Name", "").lower() or q in str(m.get("User ID")) or q in str(m.get("Phone", ""))]

    # --- Gym Info ---
    def get_gym_info(self) -> Dict[str, Any]:
        now = time.time()
        if self._info_cache and (now - self._last_info_refresh < 300):
            return self._info_cache

        info = {}
        try:
            settings = self.settings_sheet.get_all_records()
            s_map = {row["Key"]: row["Value"] for row in settings}
            info["gym_name"] = s_map.get("Gym Name", "Our Gym")
            info["contact"] = {"phone": s_map.get("Phone", ""), "email": s_map.get("Email", "")}
            info["timings"] = {"monday_to_saturday": s_map.get("Mon-Sat Timing", ""), "sunday": s_map.get("Sunday Timing", "")}
            
            fees_data = self.fees_structure_sheet.get_all_records()
            info["fees"] = {row["Plan Name"].lower().replace(" ", "_"): row["Fee Amount"] for row in fees_data}
            
            info["trainers"] = self.trainers_info_sheet.get_all_records()
            kb_data = self.kb_sheet.get_all_records()
            info["facilities"] = [row["Detail"] for row in kb_data if row["Category"] == "Facility"]
            info["rules"] = [row["Detail"] for row in kb_data if row["Category"] == "Rule"]
            info["faq"] = self.faq_sheet.get_all_records()
            
            self._info_cache = info
            self._last_info_refresh = now
        except:
             # Fallback
             return {"gym_name": "Jashpur Fitness Club"}
        return info

    def get_machines(self) -> List[Dict[str, Any]]:
        """Get all gym machines."""
        try:
            # Return machines from cached data
            return self.data.get("machines", [])
        except Exception as e:
            print(f"❌ Error getting machines: {e}")
            return []

    def log_attendance(self, user_id: int, name: str, action: str, date: str, time: str, duration: str = "N/A") -> None:
        """Log member check-in/check-out to Attendance sheet."""
        try:
            import uuid
            log_id = str(uuid.uuid4())[:8]
            
            row = [
                log_id,
                date,
                time,
                str(user_id),
                name,
                action,  # "Check In" or "Check Out"
                duration,
                "",  # Notes (empty for now)
            ]
            
            self.attendance_sheet.append_row(row)
            print(f"✅ Attendance logged: {name} - {action} at {time}")
        except Exception as e:
            print(f"❌ Failed to log attendance: {e}")

    def get_member_attendance(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get member's recent attendance records."""
        try:
            all_records = self.attendance_sheet.get_all_records()
            user_records = [
                r for r in all_records 
                if str(r.get('User ID')) == str(user_id)
            ]
            # Sort by date and time (most recent first)
            user_records.sort(key=lambda x: (x.get('Date', ''), x.get('Time', '')), reverse=True)
            return user_records[:limit]
        except:
            return []

    def get_members_with_dues(self) -> List[Dict[str, Any]]:
        """Returns members who have pending dues."""
        try:
            members_with_dues = []
            for member in self.data.get("members", []):
                # Get dues from Payment_History instead of member record
                due_date, due_amount = self.get_member_dues(member.get('User ID'))
                
                if due_amount and float(due_amount) > 0:
                    member_copy = member.copy()
                    member_copy['Due Date'] = due_date
                    member_copy['Due Amount'] = due_amount
                    members_with_dues.append(member_copy)
            
            return members_with_dues
        except Exception as e:
            print(f"❌ Error getting members with dues: {e}")
            return []

    def update_member_dues(self, user_id: int, due_date: str, due_amount: str) -> bool:
        """Update due date and amount in Payment_History (latest record)."""
        try:
            # Find the latest payment record for this user
            payments = self.payment_history_sheet.get_all_records()
            
            # Find the last row for this user
            row_idx = None
            for i in range(len(payments) - 1, -1, -1):  # Search from bottom
                if str(payments[i].get('User ID')) == str(user_id):
                    row_idx = i + 2  # +1 for 1-indexing, +1 for header
                    break
            
            if row_idx:
                # Update columns N (Due Date) and O (Due Amount)
                # Note: Payment_History has duplicate "Due Date" columns (10 and 13)
                # We update the last ones (columns 13 and 14)
                self.payment_history_sheet.update_cell(row_idx, 13, due_date)  # Column M (Due Date)
                self.payment_history_sheet.update_cell(row_idx, 14, due_amount)  # Column N (Due Amount)
                print(f"✅ Updated dues for user {user_id}: Due Date={due_date}, Due Amount={due_amount}")
                return True
            else:
                print(f"❌ No payment record found for user {user_id}")
                return False
        except Exception as e:
            print(f"❌ Failed to update dues: {e}")
            return False

    def mark_due_as_paid(self, user_id: int) -> bool:
        """Mark member's due payment as paid (set to 0)."""
        try:
            # Update Members sheet - clear due date and amount
            member = self.get_member(user_id)
            if not member:
                return False
            
            # Find member row index
            row_idx = -1
            for i, m in enumerate(self.data.get("members", [])):
                if str(m.get("User ID")) == str(user_id):
                    row_idx = i + 2  # +1 for 1-indexing, +1 for headers
                    break
            
            if row_idx == -1:
                return False
            
            # Clear due date and due amount in Members sheet
            # Assuming Due Date is column N and Due Amount is column O
            self.members_sheet.update(values=[["", "0"]], range_name=f"N{row_idx}:O{row_idx}")
            
            # Update Payment_History - set Due Payment to 0 for latest transaction
            # This part is removed as per the instruction, assuming update_member_dues will handle it
            # payment_history = self.payment_history_sheet.get_all_records()
            # for i, payment in enumerate(reversed(payment_history)):
            #     if str(payment.get('User ID')) == str(user_id):
            #         actual_row = len(payment_history) - i + 1  # +1 for header
            #         # Due Payment is column I (9th column)
            #         self.payment_history_sheet.update(values=[["0"]], range_name=f"I{actual_row}")
            #         break
            
            # Use the new helper to update the payment history
            self.update_member_dues(user_id, "", "0") # Clear due date and set amount to 0
            
            # Refresh cache
            self.refresh_cache()
            
            print(f"✅ Marked due as paid for user {user_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error marking due as paid: {e}")
            import traceback
            traceback.print_exc()
            return False

    # New session-based attendance functions
    def create_session(self, user_id: int, name: str, date: str, checkin_time: str) -> str:
        """Create a new attendance session (check-in)."""
        try:
            from datetime import datetime
            
            # Generate unique session ID
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            session_id = f"SESS_{date.replace('-', '')}_{user_id}_{timestamp}"
            
            row = [
                session_id,
                str(user_id),
                name,
                date,
                checkin_time,
                "",  # Check-Out Time (empty)
                "",  # Duration (empty)
                ""   # Notes (empty)
            ]
            
            self.attendance_sheet.append_row(row)
            print(f"✅ Session created: {session_id} - {name} checked in at {checkin_time}")
            return session_id
        except Exception as e:
            print(f"❌ Failed to create session: {e}")
            return None
    
    def get_active_session(self, user_id: int):
        """Get user's active session (checked in but not checked out)."""
        try:
            # Get all records
            records = self.attendance_sheet.get_all_records()
            
            # Find latest session for this user where Check-Out Time is empty
            for record in reversed(records):  # Start from most recent
                if str(record.get("User ID")) == str(user_id) and not record.get("Check-Out Time"):
                    return record
            
            return None
        except Exception as e:
            print(f"❌ Failed to get active session: {e}")
            return None
    
    def update_checkout(self, session_id: str, checkout_time: str, duration_mins: int) -> bool:
        """Update check-out time and duration for a session."""
        try:
            # Find the row with this session ID
            cell = self.attendance_sheet.find(session_id)
            if not cell:
                print(f"❌ Session {session_id} not found")
                return False
            
            row_num = cell.row
            
            # Update Check-Out Time (column F) and Duration (column G)
            self.attendance_sheet.update_cell(row_num, 6, checkout_time)  # Column F
            self.attendance_sheet.update_cell(row_num, 7, duration_mins)  # Column G
            
            print(f"✅ Session {session_id} updated: checked out at {checkout_time}, duration {duration_mins} mins")
            return True
        except Exception as e:
            print(f"❌ Failed to update checkout: {e}")
            return False
    
    def calculate_duration_minutes(self, checkin_time: str, checkout_time: str) -> int:
        """Calculate duration in minutes between two times (HH:MM:SS format)."""
        try:
            from datetime import datetime
            
            fmt = "%H:%M:%S"
            checkin = datetime.strptime(checkin_time, fmt)
            checkout = datetime.strptime(checkout_time, fmt)
            
            duration = checkout - checkin
            minutes = int(duration.total_seconds() / 60)
            
            return minutes
        except Exception as e:
            print(f"❌ Failed to calculate duration: {e}")
            return 0

    def get_latest_payment(self, user_id: int):
        """Get the most recent payment record for a user."""
        try:
            payments = self.payment_history_sheet.get_all_records()
            user_payments = [p for p in payments if str(p.get('User ID')) == str(user_id)]
            return user_payments[-1] if user_payments else None
        except Exception as e:
            print(f"❌ Failed to get latest payment: {e}")
            return None
    
    def get_member_dues(self, user_id: int):
        """Get due date and due amount for a member from Payment_History."""
        latest_payment = self.get_latest_payment(user_id)
        if latest_payment:
            # Payment_History has two "Due Date" columns - use the last one (column N)
            due_date = latest_payment.get('Due Date', '')
            due_amount = latest_payment.get('Due Amount', '0')
            return due_date, due_amount
        return '', '0'
