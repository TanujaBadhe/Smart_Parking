import os
import uuid
import razorpay
from dotenv import load_dotenv
from fastapi import Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from fastapi import FastAPI
from fastapi.responses import FileResponse
import auth
import database


app = FastAPI()

load_dotenv()

app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET", "supersecretkey"))

@app.on_event("startup")
async def startup():
    database.init_db()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

client = razorpay.Client(auth=(
    os.getenv("RAZORPAY_KEY_ID"),
    os.getenv("RAZORPAY_SECRET")
))

USERS_DB = {}
PARKING_DATA = database.PARKING_DATA


# ─────────────────────────────────────────────
# USER ROUTES
# ─────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def show_landing(request: Request):
    return templates.TemplateResponse(request, "landing.html", {
        "session_user": request.session.get("user")
    })


@app.get("/search", response_class=HTMLResponse)
async def search_page(request: Request, q: str = "", v_type: str = "Any", lang: str = "en"):
    if not request.session.get("user"):
        return RedirectResponse(url="/login", status_code=303)
    spots = database.get_smart_recommendations(q, v_type) or []
    recs = database.get_recommendations(spots)

    _spot_names_hi = {
        "Chakan MIDC Gate Parking": "चाकण MIDC गेट पार्किंग",
        "Chakan Market Yard Lot": "चाकण बाजार यार्ड लॉट",
        "Rajgurunagar Naka Parking": "राजगुरुनगर नाका पार्किंग",
        "Chakan MIDC Truck Bay": "चाकण MIDC ट्रक बे",
        "Chakan EV Charging Station": "चाकण EV चार्जिंग स्टेशन",
    }
    _spot_names_mr = {
        "Chakan MIDC Gate Parking": "चाकण MIDC गेट पार्किंग",
        "Chakan Market Yard Lot": "चाकण बाजार यार्ड लॉट",
        "Rajgurunagar Naka Parking": "राजगुरुनगर नाका पार्किंग",
        "Chakan MIDC Truck Bay": "चाकण MIDC ट्रक बे",
        "Chakan EV Charging Station": "चाकण EV चार्जिंग स्टेशन",
    }
    translations = {
        "en": {
            "voice": "Voice Search", "book": "Book Now", "status": "System Live",
            "reserve": "Reserve", "pay": "Pay",
            "smart_rec": "Smart Recommendations", "nearest": "Nearest",
            "most_available": "Most Available", "best_price": "Best Price",
            "occupancy_chart": "Parking Occupancy", "all_areas": "All Parking Areas",
            "found": "found", "vehicle_type": "Vehicle Type", "charge": "Charge",
            "total_slots": "Total Slots", "available": "Available", "occupancy": "Occupancy",
            "fully_booked": "Fully Booked", "full_badge": "FULL", "avail_badge": "AVAILABLE",
            "km_away": "km away", "slots_free": "slots free",
            "reserve_slot": "Reserve Your Slot", "vehicle_number": "Vehicle Number",
            "date": "Date", "start_time": "Start Time", "end_time": "End Time",
            "estimated_cost": "Estimated Cost", "check_price": "Check Price",
            "continue_pay": "Continue to Payment →", "cancel": "Cancel",
            "checkout": "Checkout", "pay_online": "Pay Now (Razorpay)",
            "pay_cod": "Pay at Parking (COD)", "no_spots": "No parking areas found",
            "no_spots_sub": "Try a different search or vehicle type",
            "clear_filters": "Clear filters", "search": "Search", "ai_search": "AI Search",
            "all_vehicles": "All Vehicles",
            "spot_names": {},
        },
        "hi": {
            "voice": "आवाज़ खोज", "book": "अभी बुक करें", "status": "सिस्टम लाइव है",
            "reserve": "आरक्षित", "pay": "भुगतान",
            "smart_rec": "स्मार्ट सुझाव", "nearest": "सबसे नज़दीक",
            "most_available": "सबसे अधिक उपलब्ध", "best_price": "सर्वोत्तम कीमत",
            "occupancy_chart": "पार्किंग उपयोग", "all_areas": "सभी पार्किंग क्षेत्र",
            "found": "मिले", "vehicle_type": "वाहन प्रकार", "charge": "शुल्क",
            "total_slots": "कुल स्लॉट", "available": "उपलब्ध", "occupancy": "उपयोग",
            "fully_booked": "पूरी तरह बुक", "full_badge": "भरा हुआ", "avail_badge": "उपलब्ध",
            "km_away": "किमी दूर", "slots_free": "स्लॉट खाली",
            "reserve_slot": "अपना स्लॉट बुक करें", "vehicle_number": "वाहन नंबर",
            "date": "तारीख", "start_time": "शुरुआत का समय", "end_time": "खत्म का समय",
            "estimated_cost": "अनुमानित लागत", "check_price": "कीमत जांचें",
            "continue_pay": "भुगतान की ओर जाएं →", "cancel": "रद्द करें",
            "checkout": "चेकआउट", "pay_online": "अभी भुगतान करें (Razorpay)",
            "pay_cod": "पार्किंग पर भुगतान करें", "no_spots": "कोई पार्किंग क्षेत्र नहीं मिला",
            "no_spots_sub": "अलग खोज या वाहन प्रकार आज़माएं",
            "clear_filters": "फ़िल्टर हटाएं", "search": "खोजें", "ai_search": "AI खोज",
            "all_vehicles": "सभी वाहन",
            "spot_names": _spot_names_hi,
        },
        "mr": {
            "voice": "व्हॉइस शोध", "book": "आता बुक करा", "status": "सिस्टम लाइव्ह आहे",
            "reserve": "आरक्षित", "pay": "पैसे भरा",
            "smart_rec": "स्मार्ट शिफारसी", "nearest": "सर्वात जवळ",
            "most_available": "सर्वाधिक उपलब्ध", "best_price": "सर्वोत्तम किंमत",
            "occupancy_chart": "पार्किंग वापर", "all_areas": "सर्व पार्किंग क्षेत्रे",
            "found": "सापडले", "vehicle_type": "वाहन प्रकार", "charge": "शुल्क",
            "total_slots": "एकूण स्लॉट", "available": "उपलब्ध", "occupancy": "वापर",
            "fully_booked": "पूर्णपणे बुक", "full_badge": "भरले", "avail_badge": "उपलब्ध",
            "km_away": "किमी दूर", "slots_free": "स्लॉट मोकळे",
            "reserve_slot": "तुमचा स्लॉट बुक करा", "vehicle_number": "वाहन क्रमांक",
            "date": "तारीख", "start_time": "सुरुवातीची वेळ", "end_time": "शेवटची वेळ",
            "estimated_cost": "अंदाजे खर्च", "check_price": "किंमत तपासा",
            "continue_pay": "पेमेंटकडे जा →", "cancel": "रद्द करा",
            "checkout": "चेकआउट", "pay_online": "आता पैसे भरा (Razorpay)",
            "pay_cod": "पार्किंगवर पैसे भरा", "no_spots": "कोणतेही पार्किंग क्षेत्र सापडले नाही",
            "no_spots_sub": "वेगळा शोध किंवा वाहन प्रकार वापरा",
            "clear_filters": "फिल्टर काढा", "search": "शोधा", "ai_search": "AI शोध",
            "all_vehicles": "सर्व वाहने",
            "spot_names": _spot_names_mr,
        },
    }
    texts = translations.get(lang, translations["en"])

    return templates.TemplateResponse(request, "index.html", {
        "spots": spots, "texts": texts, "lang": lang, "q": q, "v_type": v_type,
        "session_user": request.session.get("user"),
        "recs": recs
    })


@app.get("/api/ai-search")
async def ai_search(q: str = "", request: Request = None):
    """Rule-based AI that understands natural language parking queries."""
    import re
    query = q.lower().strip()
    v_type = "Any"
    sort_by = "distance"
    max_price = None
    require_ev = False
    require_handicap = False
    require_available = False

    # Detect vehicle type
    if any(w in query for w in ["bike", "two wheeler", "two-wheeler", "motorcycle", "scooter", "moped"]):
        v_type = "Bike"
    elif any(w in query for w in ["suv", "large", "big car", "fortuner", "innova"]):
        v_type = "SUV"
    elif any(w in query for w in ["truck", "lorry", "heavy", "tempu"]):
        v_type = "Truck"
    elif any(w in query for w in ["ev", "electric", "charging", "charge"]):
        v_type = "EV"
    elif any(w in query for w in ["car", "sedan", "hatchback", "swift"]):
        v_type = "Car"

    # Detect price intent
    if any(w in query for w in ["cheap", "cheapest", "budget", "affordable", "low cost", "less"]):
        sort_by = "price"
    if any(w in query for w in ["near", "nearest", "closest", "nearby", "close"]):
        sort_by = "distance"
    if any(w in query for w in ["available", "free", "empty", "open"]):
        require_available = True

    # Detect price ceiling e.g. "under ₹50" or "below 30" or "less than 40"
    price_match = re.search(r'(?:under|below|less than|upto|up to|max|₹|rs\.?)\s*(\d+)', query)
    if price_match:
        max_price = int(price_match.group(1))

    # Detect amenities
    if any(w in query for w in ["ev charging", "electric charging", "charger"]):
        require_ev = True
    if any(w in query for w in ["handicap", "disabled", "wheelchair", "differently abled"]):
        require_handicap = True

    spots = database.get_smart_recommendations("", v_type)

    if require_available:
        spots = [s for s in spots if s.get("rem_slots", 0) > 0]
    if max_price:
        spots = [s for s in spots if s.get("price", 9999) <= max_price]
    if require_ev:
        spots = [s for s in spots if s.get("is_ev")]
    if require_handicap:
        spots = [s for s in spots if s.get("handicap")]

    if sort_by == "price":
        spots = sorted(spots, key=lambda x: x.get("price", 9999))

    # Build a human-readable explanation
    parts = []
    if v_type != "Any": parts.append(f"{v_type} spots")
    if max_price: parts.append(f"under ₹{max_price}/hr")
    if require_ev: parts.append("with EV charging")
    if require_handicap: parts.append("handicap-friendly")
    if require_available: parts.append("with available slots")
    explanation = "Showing " + (", ".join(parts) if parts else "all spots") + f" sorted by {sort_by}"

    return {"spots": spots, "explanation": explanation, "count": len(spots)}


@app.get("/api/ai-price")
async def ai_price_suggest(v_type: str = "Car", is_ev: bool = False, is_h: bool = False, has_cctv: bool = False):
    """Suggest a fair monthly lease price based on vehicle type and amenities."""
    base = {"Bike": 1200, "Car": 2500, "SUV": 4000, "Truck": 5500, "EV": 3500}
    price = base.get(v_type, 2500)
    breakdown = [{"label": f"{v_type} base rate", "amount": price}]

    if is_ev:
        add = int(price * 0.20)
        price += add
        breakdown.append({"label": "EV Charging (+20%)", "amount": add})
    if has_cctv:
        add = int(price * 0.10)
        price += add
        breakdown.append({"label": "CCTV Security (+10%)", "amount": add})
    if is_h:
        add = int(price * 0.05)
        price += add
        breakdown.append({"label": "Handicap Friendly (+5%)", "amount": add})

    # Compare with existing leases in market
    all_spots = database.get_all_spots()
    similar = [s for s in all_spots if s.get("is_lease") and s.get("size") == v_type]
    market_avg = int(sum(s.get("price", 0) for s in similar) / len(similar)) if similar else None

    return {
        "suggested_price": price,
        "breakdown": breakdown,
        "market_avg": market_avg,
        "similar_count": len(similar),
        "tip": f"Market average for {v_type} leases in this area is ₹{market_avg}/month" if market_avg else f"Be the first to list a {v_type} spot!"
    }


@app.post("/api/chat")
async def chatbot(request: Request):
    """Rule-based parking chatbot."""
    data = await request.json()
    msg = data.get("message", "").lower().strip()

    responses = {
        ("how to book", "booking", "book a spot", "reserve", "how do i book"): (
            "🚗 To book a spot:\n1. Go to **Find Parking**\n2. Search by area or vehicle type\n3. Click **Book Now** on any available spot\n4. Enter your vehicle number & time\n5. Pay online or choose Pay at Parking (COD)"
        ),
        ("payment", "pay", "how to pay", "payment method", "razorpay", "cod", "online payment"): (
            "💳 We support two payment methods:\n• **Online (Razorpay)** — Pay securely by card/UPI/netbanking\n• **COD (Pay at Parking)** — Pay cash when you arrive\nBoth give you a confirmed booking instantly."
        ),
        ("cancel", "cancellation", "how to cancel"): (
            "❌ To cancel a booking:\n1. Go to your **Profile** → My Bookings\n2. Find the booking and click **Cancel**\nCancellation is free before your slot time."
        ),
        ("lease", "list my spot", "rent my space", "earn", "how to lease"): (
            "🏠 To lease your parking space:\n1. Click **Lease Spot** in the menu\n2. Fill in your spot details, price & dates\n3. Accept the Terms & Conditions\n4. Submit — your spot goes live immediately!"
        ),
        ("ev", "electric", "ev charging", "charger"): (
            "⚡ We have EV-enabled spots! Use the **AI Search** bar and type:\n_'EV charging spot'_ or _'electric vehicle parking'_\nSpots with the ⚡ EV badge support electric vehicle charging."
        ),
        ("price", "cost", "rate", "how much", "charges", "fee"): (
            "💰 Parking rates vary by spot:\n• Bikes: from ₹15/hr\n• Cars: from ₹30/hr\n• SUVs: from ₹60/hr\n• Trucks: from ₹80/hr\n• EV spots: from ₹50/hr\nYou can filter by **vehicle type** and sort by **cheapest** on the search page."
        ),
        ("history", "my bookings", "past bookings", "reservations"): (
            "📋 View your booking history:\n→ Click **History** in the top navigation\nYou'll see all bookings with status, payment details, and QR codes."
        ),
        ("qr", "qr code", "ticket", "pass"): (
            "📱 Your QR code is on the **Booking Confirmation** page right after booking.\nYou can also **download a PDF receipt** from the same page."
        ),
        ("profile", "account", "my account", "update profile"): (
            "👤 To update your profile:\n→ Click your name in the top-right corner\nYou can update your name, phone number, and view booking history."
        ),
        ("admin", "admin login", "dashboard"): (
            "🔐 Admin login is at **/admin/login**\nOnly authorised admins can access the dashboard."
        ),
        ("hello", "hi", "hey", "hii", "namaste", "namaskar"): (
            "👋 Hello! I'm Smart Park's AI assistant.\nI can help you with:\n• Finding & booking parking\n• Leasing your spot\n• Payment & cancellations\n• Pricing & EV spots\n\nWhat would you like to know?"
        ),
        ("thank", "thanks", "thank you", "shukriya", "dhanyawad"): (
            "😊 You're welcome! Happy to help. Drive safe! 🚗"
        ),
    }

    for keywords, reply in responses.items():
        if any(kw in msg for kw in keywords):
            return {"reply": reply}

    return {"reply": "🤔 I'm not sure about that. Try asking about:\n• **Booking a spot**\n• **Payment methods**\n• **Leasing your space**\n• **EV charging spots**\n• **Cancellations**\n• **Pricing**"}


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {
        "session_user": request.session.get("user")
    })


@app.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    return templates.TemplateResponse(request, "signup.html", {
        "session_user": request.session.get("user")
    })


@app.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request):
    return templates.TemplateResponse(request, "forgot-password.html", {
        "session_user": request.session.get("user"),
        "error": None
    })


@app.post("/forgot-password", response_class=HTMLResponse)
async def forgot_password_submit(request: Request, phone_number: str = Form(...)):
    user = database.get_user(phone_number)
    if not user:
        return templates.TemplateResponse(request, "forgot-password.html", {
            "session_user": request.session.get("user"),
            "error": "No account found with that phone number."
        })
    request.session["reset_phone"] = phone_number
    return RedirectResponse(url="/reset-password", status_code=303)


@app.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page(request: Request):
    phone = request.session.get("reset_phone")
    if not phone:
        return RedirectResponse(url="/forgot-password", status_code=303)
    return templates.TemplateResponse(request, "reset-password.html", {
        "session_user": request.session.get("user"),
        "phone": phone,
        "error": None
    })


@app.post("/reset-password", response_class=HTMLResponse)
async def reset_password_submit(
    request: Request,
    new_password: str = Form(...),
    confirm_password: str = Form(...)
):
    phone = request.session.get("reset_phone")
    if not phone:
        return RedirectResponse(url="/forgot-password", status_code=303)
    if new_password != confirm_password:
        return templates.TemplateResponse(request, "reset-password.html", {
            "session_user": request.session.get("user"),
            "phone": phone,
            "error": "Passwords do not match."
        })
    if len(new_password) < 8:
        return templates.TemplateResponse(request, "reset-password.html", {
            "session_user": request.session.get("user"),
            "phone": phone,
            "error": "Password must be at least 8 characters."
        })
    from auth import get_password_hash
    hashed = get_password_hash(new_password)
    database.update_password(phone, hashed)
    request.session.pop("reset_phone", None)
    return RedirectResponse(url="/login?msg=password_reset", status_code=303)


@app.get("/lease", response_class=HTMLResponse)
async def lease_page(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    leases = database.get_user_leases(user["phone"]) if user else []
    return templates.TemplateResponse(request, "lease.html", {
        "leases": leases,
        "session_user": user
    })


@app.post("/register")
async def register_user(request: Request,
                        name: str = Form(...),
                        phone_number: str = Form(...),
                        password: str = Form(...)):
    hashed_password = auth.get_password_hash(password)
    database.create_user(name, phone_number, hashed_password)
    request.session["user"] = {"name": name, "phone": phone_number}
    return RedirectResponse(url="/search", status_code=303)


@app.post("/submit-lease")
async def submit_lease(request: Request,
                       name: str = Form(...),
                       spot_location: str = Form(...),
                       contact_phone: str = Form(...),
                       monthly_price: float = Form(...),
                       v_type: str = Form(...),
                       allowed_vehicles: str = Form("All"),
                       lease_start_date: str = Form(...),
                       lease_end_date: str = Form(...),
                       is_ev: bool = Form(False),
                       is_h: bool = Form(False),
                       has_cctv: bool = Form(False)):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    database.add_new_lease(
        user_phone=user["phone"],
        name=name,
        spot_location=spot_location,
        contact_phone=contact_phone,
        monthly_price=monthly_price,
        size=v_type,
        is_ev=is_ev,
        is_h=is_h,
        has_cctv=has_cctv,
        lease_start_date=lease_start_date,
        lease_end_date=lease_end_date,
        allowed_vehicles=allowed_vehicles
    )
    return RedirectResponse(url="/lease", status_code=303)


@app.post("/create-order/{spot_id}")
async def create_order(spot_id: int):
    spot = database.get_spot(spot_id)
    if not spot:
        return JSONResponse(status_code=404, content={"error": "Not found"})

    if not database.is_slot_available(spot_id):
        return JSONResponse(status_code=400, content={"error": "Slot already booked"})

    receipt_id = f"RS-{uuid.uuid4().hex[:8].upper()}"

    try:
        order = client.order.create({
            "amount": int(spot["price"] * 100),
            "currency": "INR",
            "payment_capture": 1,
            "receipt": receipt_id
        })
        return {
            "order_id": order["id"],
            "amount": int(spot["price"] * 100),
            "key": os.getenv("RAZORPAY_KEY_ID"),
            "receipt_id": receipt_id,
            "spot_name": spot["name"]
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/verify-payment")
async def verify_payment(request: Request):
    data = await request.json()
    try:
        client.utility.verify_payment_signature({
            "razorpay_order_id": data["razorpay_order_id"],
            "razorpay_payment_id": data["razorpay_payment_id"],
            "razorpay_signature": data["razorpay_signature"]
        })
        spot_id = int(data.get("spot_id", 0))
        user_phone = data.get("user_phone")
        amount = int(data.get("amount", 0))
        booking_id = database.book_slot(
            spot_id, user_phone=user_phone,
            payment_id=data["razorpay_payment_id"],
            payment_method="ONLINE", amount=amount,
            vehicle_number=data.get("vehicle_number", ""),
            book_date=data.get("book_date"),
            start_time=data.get("start_time"),
            end_time=data.get("end_time")
        )
        if booking_id:
            return {"status": "success", "booking_id": booking_id}
        return {"status": "failed", "error": "Slot not available"}
    except Exception as e:
        print("Verification failed:", e)
        return {"status": "failed"}


@app.get("/reservations", response_class=HTMLResponse)
async def reservations(request: Request):
    from datetime import date, datetime, time as dt_time, timedelta
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    bookings = database.get_user_bookings(user["phone"]) if user else []
    now = datetime.now()
    for b in bookings:
        if b.get("status") == "cancelled":
            b["computed_status"] = "cancelled"
        elif b.get("book_date") and b.get("end_time"):
            try:
                et = b["end_time"]
                if isinstance(et, timedelta):
                    secs = int(et.total_seconds())
                    et = dt_time(secs // 3600, (secs % 3600) // 60, secs % 60)
                elif not isinstance(et, dt_time):
                    et = dt_time.fromisoformat(str(et))
                end_dt = datetime.combine(b["book_date"], et)
                b["computed_status"] = "ended" if now > end_dt else "active"
            except Exception:
                b["computed_status"] = "active"
        elif b.get("booking_time"):
            assumed_end = b["booking_time"] + timedelta(hours=2)
            b["computed_status"] = "ended" if now > assumed_end else "active"
        else:
            b["computed_status"] = "active"
    return templates.TemplateResponse(request, "reservations.html", {
        "session_user": user,
        "bookings": bookings,
        "today": date.today()
    })


@app.post("/cod-book/{spot_id}")
async def cod_book(spot_id: int, request: Request):
    spot = database.get_spot(spot_id)
    if not spot:
        return JSONResponse(status_code=404, content={"error": "Spot not found"})
    if not database.is_slot_available(spot_id):
        return JSONResponse(status_code=400, content={"error": "Already booked"})
    user = request.session.get("user", {})
    data = {}
    try:
        data = await request.json()
    except Exception:
        pass
    payment_id = "COD-" + uuid.uuid4().hex[:8]
    booking_id = database.book_slot(
        spot_id, user_phone=user.get("phone"),
        payment_id=payment_id, payment_method="COD",
        amount=int(data.get("amount") or spot.get("price", 0)),
        vehicle_number=data.get("vehicle_number", ""),
        book_date=data.get("book_date"),
        start_time=data.get("start_time"),
        end_time=data.get("end_time")
    )
    if booking_id:
        return {"status": "success", "booking_id": booking_id, "message": "COD booking confirmed"}
    return JSONResponse(status_code=400, content={"error": "Booking failed"})


@app.get("/booking-confirmation/{booking_id}", response_class=HTMLResponse)
async def booking_confirmation(request: Request, booking_id: int):
    booking = database.get_booking(booking_id)
    if not booking:
        return RedirectResponse(url="/search", status_code=303)
    return templates.TemplateResponse(request, "booking_confirmation.html", {
        "session_user": request.session.get("user"),
        "booking": booking
    })


@app.get("/feedback/{booking_id}", response_class=HTMLResponse)
async def feedback_page(request: Request, booking_id: int):
    booking = database.get_booking(booking_id)
    if not booking:
        return RedirectResponse(url="/search", status_code=303)
    return templates.TemplateResponse(request, "feedback.html", {
        "session_user": request.session.get("user"),
        "booking": booking
    })


@app.post("/feedback/{booking_id}")
async def submit_feedback(
    request: Request, booking_id: int,
    rating: int = Form(...),
    comment: str = Form("")
):
    user = request.session.get("user", {})
    booking = database.get_booking(booking_id)
    if booking:
        database.add_feedback(user.get("phone"), booking["spot_id"], booking_id, rating, comment)
    return RedirectResponse(url="/profile", status_code=303)


@app.get("/test-razorpay")
def test():
    try:
        order = client.order.create({"amount": 100, "currency": "INR", "payment_capture": 1})
        return {"success": True, "order": order}
    except Exception as e:
        return {"error": str(e)}


@app.get("/profile")
async def profile_page(request: Request):
    session_user = request.session.get("user")
    if not session_user:
        return RedirectResponse(url="/login", status_code=303)
    user = database.get_user(session_user["phone"]) or session_user
    bookings = database.get_user_bookings(session_user["phone"])
    return templates.TemplateResponse(request, "profile.html", {
        "user": user, "bookings": bookings, "session_user": session_user
    })


@app.post("/cancel-booking/{booking_id}")
async def cancel_booking(booking_id: int):
    database.cancel_booking(booking_id)
    return RedirectResponse(url="/profile", status_code=303)


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login")


@app.post("/update-profile")
async def update_profile(request: Request, name: str = Form(...), phone: str = Form(...)):
    session_user = request.session.get("user")
    if not session_user:
        return RedirectResponse(url="/login", status_code=303)
    database.update_user(session_user["phone"], name, phone)
    request.session["user"] = {"name": name, "phone": phone}
    return RedirectResponse(url="/profile", status_code=303)


@app.post("/cancel-lease/{lease_id}")
async def cancel_lease_route(lease_id: int, request: Request):
    user = request.session.get("user")
    if user:
        database.cancel_lease(lease_id, user["phone"])
    return RedirectResponse(url="/lease", status_code=303)


@app.post("/token")
async def login(request: Request,
                phone_number: str = Form(...),
                password: str = Form(...)):
    user = database.check_user(phone_number, password)
    if not user:
        return JSONResponse(status_code=401, content={"detail": "Incorrect phone number or password"})
    request.session["user"] = {"name": user["name"], "phone": user["phone_number"]}
    return JSONResponse({"access_token": "session", "token_type": "bearer"})


@app.post("/submit-complaint")
async def handle_complaint(issue_type: str = Form(...), description: str = Form(...)):
    print(f"New Complaint: {issue_type} - {description}")
    return RedirectResponse(url="/profile", status_code=303)


# ─────────────────────────────────────────────
# ADMIN ROUTES
# ─────────────────────────────────────────────

def admin_required(request: Request):
    return request.session.get("admin") is not None


@app.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    if admin_required(request):
        return RedirectResponse(url="/admin/dashboard", status_code=303)
    return templates.TemplateResponse(request, "admin_login.html", {"error": None})


@app.post("/admin/login", response_class=HTMLResponse)
async def admin_login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    admin = database.check_admin(username, password)
    if not admin:
        return templates.TemplateResponse(request, "admin_login.html", {"error": "Invalid credentials"})
    request.session["admin"] = {"username": admin["username"], "id": admin["id"]}
    return RedirectResponse(url="/admin/dashboard", status_code=303)


@app.get("/admin/logout")
async def admin_logout(request: Request):
    request.session.pop("admin", None)
    return RedirectResponse(url="/admin/login", status_code=303)


@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    if not admin_required(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    stats = database.get_dashboard_stats()
    chart_data = database.get_occupancy_chart_data()
    daily_data = database.get_bookings_by_day()
    return templates.TemplateResponse(request, "admin_dashboard.html", {
        "admin": request.session.get("admin"),
        "stats": stats,
        "chart_data": chart_data,
        "daily_data": daily_data
    })


@app.get("/admin/areas", response_class=HTMLResponse)
async def admin_areas(request: Request):
    if not admin_required(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    spots = database.get_all_spots()
    return templates.TemplateResponse(request, "admin_areas.html", {
        "admin": request.session.get("admin"),
        "spots": spots
    })


@app.post("/admin/areas/add")
async def admin_add_area(
    request: Request,
    name: str = Form(...),
    address: str = Form(...),
    lat: str = Form(...),
    lng: str = Form(...),
    price: int = Form(...),
    unit: str = Form("hr"),
    size: str = Form("Car"),
    is_ev: str = Form("off"),
    handicap: str = Form("off"),
    total_slots: int = Form(...),
    photo: str = Form("")
):
    if not admin_required(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    database.add_parking_area(
        name, address, lat, lng, price, unit, size,
        is_ev == "on", handicap == "on", total_slots,
        photo if photo else None
    )
    return RedirectResponse(url="/admin/areas", status_code=303)


@app.get("/admin/areas/edit/{spot_id}", response_class=HTMLResponse)
async def admin_edit_area_page(request: Request, spot_id: int):
    if not admin_required(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    spot = database.get_spot(spot_id)
    if not spot:
        return RedirectResponse(url="/admin/areas", status_code=303)
    return templates.TemplateResponse(request, "admin_area_edit.html", {
        "admin": request.session.get("admin"),
        "spot": spot
    })


@app.post("/admin/areas/edit/{spot_id}")
async def admin_edit_area_submit(
    request: Request, spot_id: int,
    name: str = Form(...),
    address: str = Form(...),
    lat: str = Form(...),
    lng: str = Form(...),
    price: int = Form(...),
    unit: str = Form("hr"),
    size: str = Form("Car"),
    is_ev: str = Form("off"),
    handicap: str = Form("off"),
    total_slots: int = Form(...),
    rem_slots: int = Form(...)
):
    if not admin_required(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    database.edit_parking_area(spot_id, name, address, lat, lng, price, unit, size,
                               is_ev == "on", handicap == "on", total_slots)
    database.update_rem_slots(spot_id, rem_slots)
    return RedirectResponse(url="/admin/areas", status_code=303)


@app.post("/admin/areas/delete/{spot_id}")
async def admin_delete_area(request: Request, spot_id: int):
    if not admin_required(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    database.delete_parking_area(spot_id)
    return RedirectResponse(url="/admin/areas", status_code=303)


@app.get("/admin/users", response_class=HTMLResponse)
async def admin_users(request: Request):
    if not admin_required(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    users = database.get_all_users()
    return templates.TemplateResponse(request, "admin_users.html", {
        "admin": request.session.get("admin"),
        "users": users
    })


@app.get("/admin/bookings", response_class=HTMLResponse)
async def admin_bookings(request: Request):
    if not admin_required(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    bookings = database.get_all_bookings_admin()
    return templates.TemplateResponse(request, "admin_bookings.html", {
        "admin": request.session.get("admin"),
        "bookings": bookings
    })


@app.get("/admin/reports", response_class=HTMLResponse)
async def admin_reports(request: Request):
    if not admin_required(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    stats = database.get_dashboard_stats()
    chart_data = database.get_occupancy_chart_data()
    daily_data = database.get_bookings_by_day()
    feedback_list = database.get_all_feedback()
    return templates.TemplateResponse(request, "admin_reports.html", {
        "admin": request.session.get("admin"),
        "stats": stats,
        "chart_data": chart_data,
        "daily_data": daily_data,
        "feedback_list": feedback_list
    })
