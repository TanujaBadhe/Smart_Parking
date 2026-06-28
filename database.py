import math
import os
import threading
import psycopg2
import psycopg2.extras
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager

lock = threading.Lock()

DATABASE_URL = os.environ.get("RAILWAY_DATABASE_URL") or os.environ.get("DATABASE_URL")

@contextmanager
def get_conn():
    conn = psycopg2.connect(DATABASE_URL)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                phone_number TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS parking_spots (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                address TEXT NOT NULL DEFAULT 'Chakan, Pune',
                lat REAL NOT NULL,
                lng REAL NOT NULL,
                price INTEGER NOT NULL,
                unit TEXT NOT NULL DEFAULT 'hr',
                size TEXT NOT NULL DEFAULT 'Car',
                is_ev BOOLEAN NOT NULL DEFAULT FALSE,
                handicap BOOLEAN NOT NULL DEFAULT FALSE,
                total_slots INTEGER NOT NULL DEFAULT 1,
                rem_slots INTEGER NOT NULL DEFAULT 1,
                photo TEXT,
                is_lease BOOLEAN NOT NULL DEFAULT FALSE
            )
        """)
        cur.execute("ALTER TABLE parking_spots ADD COLUMN IF NOT EXISTS address TEXT NOT NULL DEFAULT 'Chakan, Pune'")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id SERIAL PRIMARY KEY,
                user_phone TEXT,
                spot_id INTEGER REFERENCES parking_spots(id),
                payment_id TEXT,
                payment_method TEXT DEFAULT 'COD',
                amount INTEGER DEFAULT 0,
                booking_time TIMESTAMP DEFAULT NOW(),
                status TEXT NOT NULL DEFAULT 'active'
            )
        """)
        cur.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS payment_method TEXT DEFAULT 'COD'")
        cur.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS amount INTEGER DEFAULT 0")
        cur.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS vehicle_number TEXT DEFAULT ''")
        cur.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS book_date DATE")
        cur.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS start_time TIME")
        cur.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS end_time TIME")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS lease (
                id SERIAL PRIMARY KEY,
                user_phone VARCHAR(20) NOT NULL,
                spot_id INT NOT NULL,
                lease_start_date DATE NOT NULL,
                lease_end_date DATE NOT NULL,
                monthly_price DECIMAL(10, 2) NOT NULL,
                status VARCHAR(50) DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_phone) REFERENCES users(phone_number),
                FOREIGN KEY (spot_id) REFERENCES parking_spots(id)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS admin (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id SERIAL PRIMARY KEY,
                user_phone TEXT,
                spot_id INTEGER REFERENCES parking_spots(id),
                booking_id INTEGER REFERENCES bookings(id),
                rating INTEGER CHECK (rating >= 1 AND rating <= 5),
                comment TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute("SELECT COUNT(*) FROM parking_spots WHERE is_lease = FALSE")
        count = cur.fetchone()[0]
        if count == 0:
            cur.execute("""
                INSERT INTO parking_spots (name, address, lat, lng, price, unit, size, is_ev, handicap, total_slots, rem_slots, photo, is_lease) VALUES
                ('Chakan MIDC Gate Parking', 'MIDC Gate No.1, Chakan, Pune 410501', 18.7580, 73.8698, 60, 'hr', 'SUV', TRUE, TRUE, 50, 12,
                 'https://images.unsplash.com/photo-1506521781263-d8422e82f27a?w=800', FALSE),
                ('Chakan Market Yard Lot', 'Market Yard Road, Chakan, Pune 410501', 18.7614, 73.8631, 30, 'hr', 'Car', TRUE, FALSE, 30, 5,
                 'https://images.unsplash.com/photo-1619642751034-765dfdf7c58e?w=800', FALSE),
                ('Rajgurunagar Naka Parking', 'Rajgurunagar Naka, Pune 410505', 18.7695, 73.8753, 15, 'hr', 'Bike', FALSE, TRUE, 20, 18,
                 'https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=800', FALSE),
                ('Chakan MIDC Truck Bay', 'Industrial Area, MIDC Chakan, Pune 410501', 18.7560, 73.8720, 80, 'hr', 'Truck', FALSE, FALSE, 15, 8,
                 'https://images.unsplash.com/photo-1519003722824-194d4455a60c?w=800', FALSE),
                ('Chakan EV Charging Station', 'NH-48, Chakan, Pune 410501', 18.7630, 73.8660, 50, 'hr', 'EV', TRUE, FALSE, 10, 6,
                 'https://images.unsplash.com/photo-1593941707882-a5bba14938c7?w=800', FALSE)
                ON CONFLICT DO NOTHING
            """)
        cur.execute("SELECT COUNT(*) FROM admin")
        if cur.fetchone()[0] == 0:
            from auth import get_password_hash
            admins = [
                ("vaishnavi", "vaishnavi@#0968"),
                ("tanuja",    "tanuja@0905"),
                ("puja",      "#puja0804"),
                ("anuja",     "anuja#@1610"),
            ]
            for uname, pwd in admins:
                cur.execute("INSERT INTO admin (username, hashed_password) VALUES (%s, %s)",
                            (uname, get_password_hash(pwd)))


class _ParkingDataProxy:
    def __iter__(self):
        return iter(get_all_spots())
    def __len__(self):
        return len(get_all_spots())

PARKING_DATA = _ParkingDataProxy()


def get_all_spots():
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM parking_spots ORDER BY id")
        return [dict(r) for r in cur.fetchall()]


def get_spot(spot_id):
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM parking_spots WHERE id = %s", (spot_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def get_smart_recommendations(q="", v_type="Any", user_lat=18.7614, user_lng=73.8631):
    spots = get_all_spots()
    results = []
    for spot in spots:
        dist = math.sqrt((spot['lat'] - user_lat)**2 + (spot['lng'] - user_lng)**2)
        spot['distance'] = round(dist * 111, 1)
        name_match = q.lower() in spot['name'].lower() or q.lower() in spot.get('address', '').lower()
        size_match = (v_type == "Any" or spot['size'] == v_type)
        if name_match and size_match:
            results.append(spot)
    return sorted(results, key=lambda x: x['distance'])


def get_recommendations(spots):
    if not spots:
        return {}
    nearest = min(spots, key=lambda x: x.get('distance', 9999))
    most_available = max(spots, key=lambda x: x.get('rem_slots', 0))
    cheapest = min(spots, key=lambda x: x.get('price', 9999))
    return {
        'nearest': nearest,
        'most_available': most_available,
        'cheapest': cheapest
    }


def add_new_lease(user_phone, name, spot_location, contact_phone, monthly_price, size, is_ev, is_h, has_cctv, lease_start_date, lease_end_date, allowed_vehicles):
    with get_conn() as conn:
        cur = conn.cursor()
        full_name = f"Lease: {name}"
        cur.execute("""
            INSERT INTO parking_spots (name, address, lat, lng, price, unit, size, is_ev, handicap, total_slots, rem_slots, photo, is_lease)
            VALUES (%s, %s, 18.7620, 73.8640, %s, 'month', %s, %s, %s, 1, 1,
                    'https://images.unsplash.com/photo-1512413316925-fd4793431999?w=400', TRUE)
            RETURNING id
        """, (full_name, spot_location or 'Chakan, Pune', float(monthly_price), size, bool(is_ev), bool(is_h)))
        spot_id = cur.fetchone()[0]
        cur.execute("""
            INSERT INTO lease (user_phone, spot_id, lease_start_date, lease_end_date, monthly_price, status)
            VALUES (%s, %s, %s, %s, %s, 'active')
        """, (user_phone, spot_id, lease_start_date, lease_end_date, float(monthly_price)))
    return True


def get_user_leases(user_phone):
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT l.id, l.spot_id, l.lease_start_date, l.lease_end_date,
                   l.monthly_price, l.status, l.created_at,
                   ps.name AS spot_name, ps.size AS vehicle_type
            FROM lease l
            JOIN parking_spots ps ON l.spot_id = ps.id
            WHERE l.user_phone = %s
            ORDER BY l.created_at DESC
        """, (user_phone,))
        return cur.fetchall()


def get_all_leases():
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT l.*, ps.name AS spot_name
            FROM lease l
            JOIN parking_spots ps ON l.spot_id = ps.id
            ORDER BY l.created_at DESC
        """)
        return cur.fetchall()


def cancel_lease(lease_id, user_phone):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE lease SET status = 'cancelled', updated_at = CURRENT_TIMESTAMP
            WHERE id = %s AND user_phone = %s
        """, (lease_id, user_phone))
        cur.execute("""
            UPDATE parking_spots SET rem_slots = 0
            WHERE id = (SELECT spot_id FROM lease WHERE id = %s)
        """, (lease_id,))


def remove_lease(spot_id):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM parking_spots WHERE id = %s AND is_lease = TRUE", (spot_id,))


def book_slot(spot_id, user_phone=None, payment_id=None, payment_method='COD', amount=0, vehicle_number='', book_date=None, start_time=None, end_time=None):
    with lock:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT rem_slots FROM parking_spots WHERE id = %s FOR UPDATE", (spot_id,))
            row = cur.fetchone()
            if not row or row[0] <= 0:
                return None
            cur.execute("UPDATE parking_spots SET rem_slots = rem_slots - 1 WHERE id = %s", (spot_id,))
            cur.execute("""
                INSERT INTO bookings (user_phone, spot_id, payment_id, payment_method, amount, vehicle_number, status, book_date, start_time, end_time)
                VALUES (%s, %s, %s, %s, %s, %s, 'active', %s, %s, %s) RETURNING id
            """, (user_phone, spot_id, payment_id, payment_method, amount, vehicle_number, book_date, start_time, end_time))
            booking_id = cur.fetchone()[0]
    return booking_id


def is_slot_available(spot_id):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT rem_slots FROM parking_spots WHERE id = %s", (spot_id,))
        row = cur.fetchone()
        return row is not None and row[0] > 0


def create_user(name, phone_number, hashed_password):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO users (name, phone_number, hashed_password)
            VALUES (%s, %s, %s)
            ON CONFLICT (phone_number) DO NOTHING
        """, (name, phone_number, hashed_password))


def check_user(phone_number, password):
    from auth import verify_password
    user = get_user(phone_number)
    if user and verify_password(password, user["hashed_password"]):
        return user
    return None


def get_user(identifier):
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM users WHERE phone_number = %s", (identifier,))
        row = cur.fetchone()
        return dict(row) if row else None


def get_all_users():
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT id, name, phone_number FROM users ORDER BY id DESC")
        return [dict(r) for r in cur.fetchall()]


def get_user_bookings(user_phone):
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT b.id, b.spot_id, b.payment_id, b.payment_method, b.amount,
                   b.booking_time, b.status, p.name as spot_name, p.address as spot_address,
                   b.vehicle_number, b.book_date, b.start_time, b.end_time
            FROM bookings b
            LEFT JOIN parking_spots p ON b.spot_id = p.id
            WHERE b.user_phone = %s
            ORDER BY b.booking_time DESC
        """, (user_phone,))
        return [dict(r) for r in cur.fetchall()]


def get_booking(booking_id):
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT b.*, p.name as spot_name, p.address as spot_address, p.price as spot_price
            FROM bookings b
            LEFT JOIN parking_spots p ON b.spot_id = p.id
            WHERE b.id = %s
        """, (booking_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def cancel_booking(booking_id):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT spot_id FROM bookings WHERE id = %s AND status = 'active'", (booking_id,))
        row = cur.fetchone()
        if row:
            cur.execute("UPDATE parking_spots SET rem_slots = rem_slots + 1 WHERE id = %s", (row[0],))
        cur.execute("UPDATE bookings SET status = 'cancelled' WHERE id = %s", (booking_id,))


def update_user(old_phone, new_name, new_phone):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE users SET name = %s, phone_number = %s WHERE phone_number = %s
        """, (new_name, new_phone, old_phone))


def update_password(phone_number, new_hashed_password):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE users SET hashed_password = %s WHERE phone_number = %s
        """, (new_hashed_password, phone_number))


def check_admin(username, password):
    from auth import verify_password
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM admin WHERE username = %s", (username,))
        row = cur.fetchone()
        if row and verify_password(password, row["hashed_password"]):
            return dict(row)
    return None


def get_dashboard_stats():
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM parking_spots WHERE is_lease = FALSE")
        total_areas = cur.fetchone()[0]
        cur.execute("SELECT COALESCE(SUM(total_slots), 0) FROM parking_spots WHERE is_lease = FALSE")
        total_slots = cur.fetchone()[0]
        cur.execute("SELECT COALESCE(SUM(rem_slots), 0) FROM parking_spots WHERE is_lease = FALSE")
        available_slots = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM bookings WHERE status = 'active'")
        total_bookings = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM users")
        total_users = cur.fetchone()[0]
        return {
            'total_areas': total_areas,
            'total_slots': total_slots,
            'available_slots': available_slots,
            'occupied_slots': total_slots - available_slots,
            'total_bookings': total_bookings,
            'total_users': total_users
        }


def get_all_bookings_admin():
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT b.id, b.user_phone, b.payment_id, b.payment_method, b.amount,
                   b.booking_time, b.status, p.name as spot_name
            FROM bookings b
            LEFT JOIN parking_spots p ON b.spot_id = p.id
            ORDER BY b.booking_time DESC
        """)
        return [dict(r) for r in cur.fetchall()]


def add_parking_area(name, address, lat, lng, price, unit, size, is_ev, handicap, total_slots, photo=None):
    if not photo:
        photo = 'https://images.unsplash.com/photo-1565793298595-6a879b1d9492?w=800'
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO parking_spots (name, address, lat, lng, price, unit, size, is_ev, handicap, total_slots, rem_slots, photo, is_lease)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, FALSE)
        """, (name, address, float(lat), float(lng), int(price), unit, size,
              bool(is_ev), bool(handicap), int(total_slots), int(total_slots), photo))


def edit_parking_area(spot_id, name, address, lat, lng, price, unit, size, is_ev, handicap, total_slots):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE parking_spots SET name=%s, address=%s, lat=%s, lng=%s, price=%s,
            unit=%s, size=%s, is_ev=%s, handicap=%s, total_slots=%s
            WHERE id=%s
        """, (name, address, float(lat), float(lng), int(price), unit, size,
              bool(is_ev), bool(handicap), int(total_slots), spot_id))


def update_rem_slots(spot_id, rem_slots):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE parking_spots SET rem_slots = %s WHERE id = %s", (int(rem_slots), spot_id))


def delete_parking_area(spot_id):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM bookings WHERE spot_id = %s", (spot_id,))
        cur.execute("DELETE FROM feedback WHERE spot_id = %s", (spot_id,))
        cur.execute("DELETE FROM parking_spots WHERE id = %s", (spot_id,))


def add_feedback(user_phone, spot_id, booking_id, rating, comment):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO feedback (user_phone, spot_id, booking_id, rating, comment)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_phone, spot_id, booking_id, int(rating), comment))


def get_all_feedback():
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT f.*, p.name as spot_name
            FROM feedback f
            LEFT JOIN parking_spots p ON f.spot_id = p.id
            ORDER BY f.created_at DESC
        """)
        return [dict(r) for r in cur.fetchall()]


def get_occupancy_chart_data():
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT name,
                   total_slots - rem_slots AS occupied,
                   rem_slots AS available
            FROM parking_spots
            WHERE is_lease = FALSE
            ORDER BY id
        """)
        return [dict(r) for r in cur.fetchall()]


def get_bookings_by_day():
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT TO_CHAR(DATE(booking_time), 'DD Mon') as day, COUNT(*) as count
            FROM bookings
            WHERE booking_time >= NOW() - INTERVAL '7 days'
            GROUP BY DATE(booking_time)
            ORDER BY DATE(booking_time)
        """)
        return [dict(r) for r in cur.fetchall()]
