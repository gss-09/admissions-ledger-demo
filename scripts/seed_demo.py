"""Seed the DEMO database with rich, entirely FICTIONAL sample data.

This repository is a public example of a system that runs in production for an
educational institution serving 2,000-3,000 students (the production instance
tracks 1,400+ real applicants). Every name, phone number and rupee figure
created here is invented — no real data is used anywhere.

The seed exercises every feature of the app: the City -> Campus -> Course org
hierarchy, field + staff AGM teams with city bindings and rent, marketing execs
with the full cost breakdown (salary / general expenditure / incentive / gift)
and admission targets, ~1,500 applicants across every funnel stage with fees and
hostel choices, city-bound user accounts, and activity/login/password logs —
so the Home, Students, AGMs, Execs, Averages, Income and Expenditure screens all
have data to show.

Usage (point DATABASE_URL at an EMPTY Postgres database):
    DATABASE_URL="postgresql://..." python3 scripts/seed_demo.py

Demo credentials created:
    Public (shown on the login screen):
        viewer / Demo@1234          (read-only everywhere)
    Privileged (NEVER published — this is a public repo, so every account that
    can EDIT data gets a private password): set DEMO_ADMIN_PASSWORD (and
    optionally DEMO_ADMIN_USERNAME) in the environment before seeding, or the
    script generates a random password and prints it once at the end.
"""

import itertools
import os
import random
import secrets
import sys
from datetime import timedelta

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from app import db, security       # noqa: E402
from app.schema import init_db     # noqa: E402
from app.config import STATUSES    # noqa: E402

random.seed(7)

# Read-only viewer — the ONLY credential published on the login screen/README.
VIEWER_PASSWORD = "Demo@1234"

# Accounts that can EDIT data (admin + editors) get a PRIVATE password: this
# repo is public, so a hard-coded value here would hand write access to anyone.
ADMIN_USERNAME = os.environ.get("DEMO_ADMIN_USERNAME", "ledger.admin").strip()
ADMIN_PASSWORD = os.environ.get("DEMO_ADMIN_PASSWORD") or secrets.token_urlsafe(12)

FIRST = ["Aarav", "Vihaan", "Ishaan", "Rohan", "Aditya", "Nikhil", "Karthik",
         "Rahul", "Varun", "Tejas", "Manish", "Praveen", "Vamsi", "Harsha",
         "Ananya", "Diya", "Kavya", "Sneha", "Meera", "Priya", "Divya",
         "Sanjana", "Lakshmi", "Pooja", "Nandini", "Swathi", "Keerthi",
         "Anjali", "Bhavana", "Chandana", "Deepika", "Gowri", "Hansika",
         "Jaswanth", "Kiran", "Lokesh", "Mounika", "Nithya", "Pranav",
         "Ritika", "Sahithi", "Tanvi", "Uday", "Vaishnavi", "Yashwanth",
         "Advait", "Akhila", "Amrutha", "Arnav", "Bhavesh", "Charan",
         "Darshan", "Esha", "Gautham", "Hemanth", "Jahnavi", "Kalyani",
         "Lavanya", "Madhav", "Omkar"]
LAST = ["Rao", "Reddy", "Sharma", "Varma", "Naidu", "Iyer", "Menon", "Gupta",
        "Patel", "Chowdary", "Kumar", "Prasad", "Murthy", "Sastry", "Pillai",
        "Nair", "Joshi", "Kulkarni", "Deshmukh", "Bhat",
        "Agarwal", "Banerjee", "Bhandari", "Chauhan", "Desai", "Dutta",
        "Ghosh", "Hegde", "Jain", "Kamath", "Kapoor", "Khanna", "Mishra",
        "Pandey", "Rathore", "Saxena", "Shetty", "Sinha", "Tripathi",
        "Trivedi", "Verma"]
FATHER_FIRST = ["Ramesh", "Suresh", "Mahesh", "Rajesh", "Ganesh", "Prakash",
                "Srinivas", "Venkatesh", "Mohan", "Krishna", "Ravindra",
                "Narayana", "Sudhakar", "Chandra", "Bhaskar"]

# The fictional recruiting org.
CITIES = {
    "NORTHVALE": ["NORTHVALE DS", "NORTHVALE HOSTEL"],
    "EASTPORT":  ["EASTPORT DS"],
    "WESTBROOK": ["WESTBROOK DS"],
}
CAMPUS_COURSES = {
    "NORTHVALE DS":     ["MPC", "BIPC", "MEC", "CEC"],
    "NORTHVALE HOSTEL": ["MPC", "BIPC"],
    "EASTPORT DS":      ["MPC", "BIPC"],
    "WESTBROOK DS":     ["MPC"],
}
# AGM teams: (name, city, is_field, rent). Field teams recruit on the ground and
# carry premises rent; the staff team's salaries are not an admission cost.
AGMS = [
    ("ARJUN MEHTA",  "NORTHVALE", 1, 45000),
    ("BHARGAV RAJU", "NORTHVALE", 1, 38000),
    ("CHITRA NAIR",  "EASTPORT",  1, 30000),
    ("DINESH RAWAL", "WESTBROOK", 1, 25000),
    ("CAMPUS STAFF", "NORTHVALE", 0, 0),
]
EXECS_PER_AGM = (3, 5)


# Every applicant/exec draws from one shuffled pool of all FIRST x LAST
# combinations, so no two generated people ever share a name.
_NAME_POOL = [f"{f} {l}" for f, l in itertools.product(FIRST, LAST)]
random.shuffle(_NAME_POOL)


def unique_name():
    return _NAME_POOL.pop()


def fake_phone():
    return "9" + "".join(random.choice("0123456789") for _ in range(9))


def day(offset):
    return (db.now_dt() - timedelta(days=offset)).strftime("%Y-%m-%d")


def main():
    if not os.environ.get("DATABASE_URL"):
        sys.exit("Set DATABASE_URL to an EMPTY demo Postgres database first.")

    if security.password_too_short(ADMIN_PASSWORD):
        sys.exit("DEMO_ADMIN_PASSWORD must be at least "
                 f"{security.MIN_PASSWORD_LEN} characters.")
    if not ADMIN_USERNAME or ADMIN_USERNAME == "viewer":
        sys.exit("DEMO_ADMIN_USERNAME must be a non-empty name other than 'viewer'.")

    print("Initialising schema ...")
    init_db()
    viewer_hash = security.hash_password(VIEWER_PASSWORD)
    admin_hash = security.hash_password(ADMIN_PASSWORD)

    with db.connect() as conn:
        seed(conn, viewer_hash, admin_hash)
        conn.commit()

    print("Demo data seeded.")
    print(f"  Public sign-in (read-only): viewer / {VIEWER_PASSWORD}")
    print(f"  Administrator (KEEP PRIVATE): {ADMIN_USERNAME} / {ADMIN_PASSWORD}")
    print("  (editor / editor.northvale share the administrator password)")


def seed(conn, viewer_hash, admin_hash):
    now = db.now()

    conn.execute(
        "INSERT INTO settings (key, value) VALUES ('demo_notice', ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        ("EXAMPLE DATABASE — every record here is fictional sample data. "
         "This public repository mirrors a system already running in production "
         "for an educational institution with 2,000-3,000 students.",))

    # ---- Cities, campuses, courses (init_db seeded some; make sure of all) --
    city_ids, campus_ids = {}, {}
    for city, campuses in CITIES.items():
        row = conn.execute("SELECT id FROM cities WHERE name = ?", (city,)).fetchone()
        city_ids[city] = row["id"] if row else db.insert(
            conn, "INSERT INTO cities (name, created_at) VALUES (?, ?)", (city, now))
        for campus in campuses:
            row = conn.execute("SELECT id FROM campuses WHERE name = ?",
                               (campus,)).fetchone()
            cid = row["id"] if row else db.insert(
                conn, "INSERT INTO campuses (name, created_at) VALUES (?, ?)",
                (campus, now))
            campus_ids[campus] = cid
            conn.execute("UPDATE campuses SET city_id = ? WHERE id = ?",
                         (city_ids[city], cid))
    for campus, courses in CAMPUS_COURSES.items():
        for course in courses:
            conn.execute(
                "INSERT INTO courses (campus_id, name, created_at) VALUES (?, ?, ?) "
                "ON CONFLICT (campus_id, name) DO NOTHING",
                (campus_ids[campus], course, now))

    # ---- Users: admin + editor + city-bound editor + viewer -----------------
    # Rename the first-run 'admin' account and give every edit-capable account
    # the private password; only the read-only viewer gets the published one.
    conn.execute("UPDATE users SET username = ?, password_hash = ? "
                 "WHERE username IN ('admin', ?)",
                 (ADMIN_USERNAME, admin_hash, ADMIN_USERNAME))
    users = [("editor", "Meghana Kulkarni", "editor", admin_hash),
             ("editor.northvale", "Sameer Joshi", "editor", admin_hash),
             ("viewer", "Anita Bhat", "viewer", viewer_hash)]
    for username, full, role, phash in users:
        if not conn.execute("SELECT 1 FROM users WHERE username = ?",
                            (username,)).fetchone():
            conn.execute(
                "INSERT INTO users (username, full_name, role, password_hash, "
                "created_at) VALUES (?, ?, ?, ?, ?)",
                (username, full, role, phash, now))
        else:
            conn.execute("UPDATE users SET password_hash = ? WHERE username = ?",
                         (phash, username))
    bound = conn.execute("SELECT id FROM users WHERE username = 'editor.northvale'"
                         ).fetchone()
    conn.execute(
        "INSERT INTO user_cities (user_id, city_id) VALUES (?, ?) "
        "ON CONFLICT (user_id, city_id) DO NOTHING",
        (bound["id"], city_ids["NORTHVALE"]))

    admin = conn.execute("SELECT id FROM users WHERE username = ?",
                         (ADMIN_USERNAME,)).fetchone()
    conn.execute(
        "INSERT INTO password_changes (target_user_id, target_name, "
        "target_username, actor_user_id, actor_name, actor_username, kind, "
        "created_at) VALUES (?, 'Anita Bhat', 'viewer', ?, 'Administrator', "
        "?, 'reset', ?)", (bound["id"], admin["id"], ADMIN_USERNAME, now))

    # ---- AGM teams + marketing execs (full cost breakdown) ------------------
    agm_execs = {}     # agm name -> [exec names]
    for name, city, is_field, rent in AGMS:
        row = conn.execute("SELECT id FROM agms WHERE name = ?", (name,)).fetchone()
        agm_id = row["id"] if row else db.insert(
            conn, "INSERT INTO agms (name, created_at) VALUES (?, ?)", (name, now))
        conn.execute("UPDATE agms SET city_id = ?, is_field = ?, rent = ? "
                     "WHERE id = ?", (city_ids[city], is_field, rent, agm_id))
        agm_execs[name] = []
        for _ in range(random.randint(*EXECS_PER_AGM)):
            ename = unique_name().upper()
            gen_exp = random.randrange(3000, 9000, 500)
            incentive = random.randrange(0, 12000, 1000)
            gift = random.randrange(0, 4000, 500)
            if is_field:
                salary = random.randrange(18000, 32000, 1000)
                total = salary + gen_exp + incentive + gift
            else:
                salary = None                      # staff salary ≠ admission cost
                total = gen_exp + incentive + gift
            conn.execute(
                "INSERT INTO execs (agm_id, name, created_at, salary, gen_exp, "
                "incentive, gift, total_amount, target) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT (agm_id, name) DO NOTHING",
                (agm_id, ename, now, salary, gen_exp, incentive, gift, total,
                 random.randint(25, 80)))
            agm_execs[name].append(ename)

    # ---- Applicants: ~1,500 fictional rows across the whole funnel ----------
    # (campus, weight) — most volume at the NORTHVALE campuses.
    campus_mix = [("NORTHVALE DS", 55), ("NORTHVALE HOSTEL", 20),
                  ("EASTPORT DS", 15), ("WESTBROOK DS", 10)]
    status_mix = [("REPORTED", 52), ("SETTLED", 14), ("YET TO ARRIVE", 16),
                  ("NOT LIFTING", 11), ("DROPPED", 7)]
    raw_variants = {
        "REPORTED":      ["REPORTED", "REPORTED - JOINED", "REPORTED (HOSTEL)"],
        "SETTLED":       ["SETTLED", "FEE SETTLED"],
        "YET TO ARRIVE": ["YET TO ARRIVE", "WILL COME AFTER RESULTS"],
        "NOT LIFTING":   ["NOT LIFTING", "SWITCHED OFF", "NO RESPONSE"],
        "DROPPED":       ["DROPPED", "JOINED ELSEWHERE"],
    }
    campus_by_city = {c: city for city, cs in CITIES.items() for c in cs}
    agms_by_city = {}
    for name, city, is_field, rent in AGMS:
        agms_by_city.setdefault(city, []).append(name)

    total = 1500
    print(f"Seeding {total} fictional applicants ...")
    rows = []
    for i in range(1, total + 1):
        campus = random.choices([c for c, _ in campus_mix],
                                [w for _, w in campus_mix])[0]
        status = random.choices([s for s, _ in status_mix],
                                [w for _, w in status_mix])[0]
        assert status in STATUSES
        agm = random.choice(agms_by_city[campus_by_city[campus]])
        exec_name = random.choice(agm_execs[agm])
        course = random.choice(CAMPUS_COURSES[campus])
        name = unique_name().upper()
        reported = (day(random.randint(0, 45))
                    if status in ("REPORTED", "SETTLED") else None)
        fee = (random.randrange(45000, 86000, 500)
               if status in ("REPORTED", "SETTLED") else None)
        hostel = (random.choice(("AC", "NON-AC"))
                  if "HOSTEL" in campus or random.random() < 0.35 else None)
        rows.append((f"26A{i:04d}", name,
                     f"{random.choice(FATHER_FIRST)} {name.split()[-1]}".upper(),
                     course, course, fake_phone(),
                     fake_phone() if random.random() < 0.4 else None,
                     agm, exec_name, campus, fee, hostel,
                     random.choice(raw_variants[status]), status, reported,
                     0, "demo-seed", now))
    cur = conn.raw.cursor()
    cur.executemany(
        "INSERT INTO students (appn_no, student_name, father_name, grp, "
        "application_course, mobile1, mobile2, agm, marketing_exec, campus, "
        "final_fee, hostel, status_raw, status_category, reported_date, hidden, "
        "registered_by, registered_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, "
        "%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", rows)

    # ---- Activity + login logs ----------------------------------------------
    log_users = [(ADMIN_USERNAME, "Administrator", "admin"),
                 ("editor", "Meghana Kulkarni", "editor"),
                 ("editor.northvale", "Sameer Joshi", "editor")]
    edits = [("students", "student_update", "Updated an admission"),
             ("students", "student_add", "Added an admission"),
             ("org", "exec_create", "Added a marketing exec"),
             ("org", "campus_rename", "Renamed a campus")]
    for _ in range(15):
        uname, full, role = random.choice(log_users)
        module, action, detail = random.choice(edits)
        u = conn.execute("SELECT id FROM users WHERE username = ?", (uname,)).fetchone()
        conn.execute(
            "INSERT INTO edit_log (user_id, username, full_name, role, module, "
            "action, detail, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (u["id"], uname, full, role, module, action, detail,
             day(random.randint(0, 12)) + f" {random.randint(9, 19):02d}:{random.randint(0, 59):02d}"))
    for _ in range(10):
        uname, full, role = random.choice(log_users)
        u = conn.execute("SELECT id FROM users WHERE username = ?", (uname,)).fetchone()
        conn.execute(
            "INSERT INTO login_log (user_id, username, full_name, role, event, "
            "ip, created_at) VALUES (?, ?, ?, ?, 'login', '203.0.113.20', ?)",
            (u["id"], uname, full, role,
             day(random.randint(0, 8)) + f" {random.randint(8, 20):02d}:40"))


if __name__ == "__main__":
    main()
