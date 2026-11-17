# Bareeq — Product Spec (v1, 17 Nov 2026)

Mobile car wash at the customer's home. The customer books from the app, a technician comes with the equipment.
Launch areas: **Nasr City, Obour, Madinaty**. Launch team: **5 technicians**.
Source: the client study written for John (Arabic) and the client's answers of 17 Nov 2026.

---

## 1. Roles (one Flutter app, screens chosen by role after login)

| Role | How the account is created | Main screens |
| --- | --- | --- |
| Customer | Self sign-up in the app | Book, my orders, my cars, my addresses, wallet, referral code, ratings, notifications |
| Technician | Manager adds his phone number; cannot self-register | Today's jobs in order, map + "navigate" button, status buttons, before/after photos, "car not found", daily cash closing |
| Manager | Created by us (seed / Django admin) | Everything, in the app (quick view) and in the web dashboard (full) |
| Supervisor (phase 4) | Manager creates | Assign/move jobs between technicians. No prices, no revenue |

Login for all roles: phone number + one-time code.

## 2. Sign-up and onboarding (customer)

1. **Terms screen first**: the customer reads the terms and cancellation rules (text is a setting, edited by the manager) and must tick "I agree" before anything else. Store the accepted terms version + timestamp.
2. **Sign-up screen**: phone number + one-time code, full name. Optional: referral code (auto-filled when opened from a referral link), "how did you hear about us" (list editable by the manager).
3. **One-time code delivery**: by SMS. The SMS provider is NOT chosen yet (open question). Build an `OtpSender` interface; in development, log the code to the console. Rate-limit requests per phone and per device.
4. **Right after sign-up**: two short steps, "your car" and "your address" (sections 3 and 4). The customer may skip and browse, but cannot book until both exist.
5. Collected silently: sign-up date, device type, order count, total paid, last order date.
6. No email, no password.

## 3. Cars (no typing)

- Pick in order: **brand → model → year → color**, each list searchable.
- Every model in the catalog has a **size class**: `hatchback`, `sedan`, `suv`, `luxury`. The customer is never asked the size; price and duration follow from it.
- Seed the catalog with the brands/models common in Egypt; the manager can add brands/models and set their size class.
- Last option in the model list: "My model isn't listed" → the customer picks the size himself, the manager gets a notification to review and add the model.
- Optional plate number.
- "Where does the car park?": closed garage / open garage / street (affects which services are allowed, e.g. polishing needs shade; manager can flag services as "needs shade").
- A customer can have several cars and book several cars in one order (same address, consecutive time on the same technician).

## 4. Addresses and zones (Google Maps)

- Map opens on current location (if permitted) or a search box with Places autocomplete. Customer drags the pin to the exact spot, then adds building number, floor, landmark. Saved addresses with labels (Home, Work, ...).
- **Zones are polygons drawn on a map in the manager dashboard**, not names. The zone of an address = the polygon containing the pin.
- Pin outside all zones → "We're not in your area yet" + "Notify me when you arrive" (store these requests; manager sees them as a demand list).
- Technician sees the same pin; "Navigate" opens Google Maps on his phone.

## 5. Services, prices, durations

- Services (initial list, editable): exterior wash, interior wash, engine wash, exterior detailing, interior detailing, polish & protection (wax/ceramic), headlight restoration, **oil change** (company supplies the oil at cost; oil type/grade chosen by the customer; oil price shown separately from labor).
- **Price = setting per service × zone × car size.** Edited from a "Prices" section in the dashboard.
- **Duration = setting per service × car size** (minutes). Initial values are estimates to be tuned from real jobs; the dashboard should show average actual job time per service/size from completed orders to help tuning.
- Rules between services (settings):
  - "replaces": exterior detailing replaces exterior wash; interior detailing replaces interior wash. Selecting one auto-removes the other with a short message.
  - "needs shade": blocked or warned when the car parks on the street.
- Bundles (e.g. basic = exterior + interior) with a discount %, editable.
- Sticky bottom bar on the services screen shows live total price and total duration.

## 6. Scheduling (core logic — write tests first)

Goal: never offer a time a technician can't actually make.

- Each technician has: working hours per weekday, days off, start location (shop or home), zones he covers.
- A job occupies a technician from `start` to `start + total_duration`.
- **Earliest next start for a technician** =
  `max( previous_job_end + travel_time(prev_address → next_address) + buffer, previous_job_start + min_gap )`
  - `travel_time` from Google Routes (traffic-aware), cached per address pair per hour-of-day.
  - `buffer` = setting (default 15 min). `min_gap` = setting (default 90 min, the client's original rule).
  - First job of the day: travel from the technician's start location.
- **Slots shown to the customer** = times where at least one technician covering that zone is free for the whole job duration (including travel), within his working hours. Number of parallel bookings at a time = number of free technicians in that zone.
- Slots that can't fit the selected services before the end of working hours are hidden.
- **Slot hold**: choosing a slot reserves it for 10 minutes while the customer completes payment; expires automatically.
- **Auto-assign** the job to the nearest free technician. Manager/supervisor can move a job to another technician; the customer gets a notification with the new technician's name.
- **Express order (phase 4)**: shown only if a technician is free now and can arrive within 90 minutes (setting); otherwise hidden and the nearest slot is suggested. Express fee per zone = setting.
- Example to use as a test case (one technician, Nasr City): A = exterior wash 10:00–10:45, travel 20 min → next earliest 11:30 (min_gap wins). B = exterior detailing 11:30–14:30, travel 25 min → next earliest 15:10 (not 13:00).

## 7. Order lifecycle

Statuses: `pending_payment` → `confirmed` → `on_the_way` → `arrived` → `in_progress` → `completed`; side exits: `cancelled_by_customer`, `cancelled_by_company`, `car_not_found`.

- Technician cannot press "start" before uploading **4 "before" photos** (front, back, both sides); cannot press "done" before 4 "after" photos.
- "Car not found": records time + GPS, notifies customer and manager; can trigger the late-cancellation fee.
- Cancellation/reschedule rules (settings): free until X hours before; after that a fee. The text the customer agreed to in sign-up is the reference.
- Bad weather: manager can close a day or a zone; affected customers get a notification to pick a new time.

## 8. Payments

Phase 1: **cash** to the technician, **wallet balance**, and **InstaPay link**.
- InstaPay is not confirmed automatically: the customer uploads the transfer screenshot; the order shows "awaiting confirmation"; the manager confirms with one tap.
- Invoice separates: services, discounts, wallet used, amount paid in cash/InstaPay.
- **Technician daily closing**: cash collected per order, materials used; manager confirms receipt. Difference report.
- Card/e-wallet gateway: phase 3.

## 9. Notifications

**No WhatsApp for now.** All messages are push notifications (Firebase Cloud Messaging) + an in-app notifications list:
welcome after sign-up, booking confirmed, reminder 1 hour before, technician on the way (with name), job done + rating link, wallet credit/expiry reminder, "time for your next wash" after 14 days (setting). Keep a `Notifier` interface so WhatsApp can be added later.

## 10. Ratings

- After `completed`: 1–5 stars + quick tags (on time, quality, manners, cleanliness around the car) + optional text.
- ≤ 3 stars → instant alert to manager + "call me" button + photo upload for the customer.
- 5 stars → polite prompt to leave a Google Maps review. No reward for it.
- One reminder if not rated within 24 h.
- Manager: average per technician / zone / service, and a list of unhandled bad ratings.

## 11. Wallet, cashback, referral, loyalty (phase 2 — but design the tables in phase 1)

Client decision: all of this is configured from **system settings**.
- Wallet holds **gift balance only** (cashback, referral bonus, refunds). No top-up with real money (legal question still open).
- Every change is a ledger row: `customer, amount, type (cashback|referral|refund|spend|expiry|manual), order, expires_at, created_by`. Balance = sum of non-expired rows.
- Rules (all settings): no cash withdrawal; max share of an order payable from wallet (default 50%); expiry (default 90 days per credit, reminder 7 days before); cashback % credited only after the order is `completed` and paid.
- Cancelled order paid online → customer chooses refund to original method or to wallet (+ bonus %, setting).
- Referral: fixed code + share link; new customer gets a first-order discount; referrer gets credit **only after the new customer's first paid, completed order**. Fraud checks: same address, same plate, same device → no credit; monthly cap (setting), above it → manager review.
- Loyalty: wash card (every N washes, next one X% off or free) and/or cashback %. Both switchable in settings.
- Coupons: % or amount, zone, usage limit, expiry.
- Manager report: open wallet liability today; credited / spent / expired this month by type.

## 12. Manager web dashboard (Next.js)

Today's orders (map + list), technicians and their schedules, move a job, confirm InstaPay payments, confirm daily closings, customers (profile: orders, ratings, wallet, notes), prices (service × zone × size), durations (service × size), zones (draw polygons), working hours/days off, service rules, bundles, coupons, loyalty/referral/cashback settings, terms text, "notify me" demand list, ratings, reports (revenue per day/month/zone/technician/service, new vs returning customers, bonus cost, km driven per technician).

## 13. Google Maps usage and cost control

Maps SDK in the app (free), Places Autocomplete, Geocoding, Routes (Compute Route Matrix). Cache travel times; set a monthly budget cap in Google Cloud. Reference prices (Nov 2026): each of Autocomplete, Geocoding, Route Matrix has 10,000 free requests/month, then about $2.83–$5 per 1,000 (https://developers.google.com/maps/billing/pricing).

## 14. Phases

1. **Operations**: roles, OTP login, terms, cars catalog, addresses/zones, services/prices/durations as settings, scheduling, technician flow with photos, daily closing, push notifications, ratings, cash + wallet field + InstaPay with manual confirm, basic dashboard.
2. **Retention**: wallet ledger, cashback, referral, wash card, coupons, win-back and next-wash notifications.
3. **Payments & subscription**: card/e-wallet gateway, monthly subscription (e.g. 4 washes/month, fixed weekly slot).
4. **Scale**: live technician tracking, express orders, supervisor role, detailed reports, distance fee.

## 15. Open questions (ask John before building these parts)

- SMS provider for the one-time code.
- Which technician covers which zone (5 technicians).
- Final cancellation terms text and fees.
- Where to host (server) and the store accounts (Apple, Google Play) — must be in the client's name.
