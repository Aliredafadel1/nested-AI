-- NestAI Realistic Seed Data — Lebanon-specific student housing
-- All demo passwords: Demo1234!
-- Requires migrations/init.sql to have run first (neighborhoods + universities seeded)
-- Idempotent: safe to run multiple times

-- ─── USERS ───────────────────────────────────────────────────────────────────

INSERT INTO users (id, email, password_hash, role) VALUES
    -- Landlords (6 total — 5 legitimate, 1 scammer for fraud testing)
    (1, 'landlord@demo.com',  '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMzLMEFOwqFe6rQl2F9pCVoW4G', 'landlord'),
    (3, 'khalil@demo.com',    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMzLMEFOwqFe6rQl2F9pCVoW4G', 'landlord'),
    (4, 'mona@demo.com',      '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMzLMEFOwqFe6rQl2F9pCVoW4G', 'landlord'),
    (5, 'georges@demo.com',   '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMzLMEFOwqFe6rQl2F9pCVoW4G', 'landlord'),
    (6, 'rania@demo.com',     '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMzLMEFOwqFe6rQl2F9pCVoW4G', 'landlord'),
    (7, 'scammer@demo.com',   '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMzLMEFOwqFe6rQl2F9pCVoW4G', 'landlord'),
    -- Students (5 total — diverse preferences for roommate matching tests)
    (2,  'jawad@demo.com',   '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMzLMEFOwqFe6rQl2F9pCVoW4G', 'student'),
    (8,  'omar@demo.com',   '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMzLMEFOwqFe6rQl2F9pCVoW4G', 'student'),
    (9,  'maya@demo.com',   '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMzLMEFOwqFe6rQl2F9pCVoW4G', 'student'),
    (10, 'karim@demo.com',  '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMzLMEFOwqFe6rQl2F9pCVoW4G', 'student'),
    (11, 'sarah@demo.com',  '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMzLMEFOwqFe6rQl2F9pCVoW4G', 'student')
ON CONFLICT (id) DO NOTHING;

-- ─── LANDLORD PROFILES ────────────────────────────────────────────────────────

INSERT INTO landlord_profiles (user_id, phone, phone_verified, reputation_score) VALUES
    (1, '+961 3 123 456', true,  4.70),
    (3, '+961 70 234 567', true,  4.50),
    (4, '+961 3 345 678', true,  4.80),
    (5, '+961 71 456 789', false, 4.20),
    (6, '+961 3 567 890', true,  4.60),
    (7, '+961 99 000 111', false, 0.00)  -- scammer: no verification
ON CONFLICT (user_id) DO NOTHING;

-- ─── STUDENT PROFILES ────────────────────────────────────────────────────────
-- Diverse preferences to produce meaningful roommate matching dimension scores

INSERT INTO student_profiles (user_id, university_id, budget_min, budget_max, sleep_schedule, study_habits, cleanliness, guests, language, priorities) VALUES
    -- Jawad: AUB, night owl, quiet studier, high cleanliness, rarely hosts
    (2,  1, 400, 700, 'night_owl',  'quiet',    'high',   'rarely',    'mixed',   '["proximity_to_university","generator_coverage","quiet_environment"]'),
    -- Omar: LAU Beirut, early bird, quiet, medium cleanliness, sometimes hosts — opposite sleep from Jawad
    (8,  2, 300, 500, 'early_bird', 'quiet',    'medium', 'sometimes', 'arabic',  '["affordable_rent","proximity_to_university","public_transport"]'),
    -- Maya: USJ, flexible, social, low cleanliness, often hosts — social butterfly
    (9,  3, 500, 800, 'flexible',   'moderate', 'low',    'often',     'french',  '["social_environment","furnished","near_cafes"]'),
    -- Karim: LU Hadath, night owl, flexible, medium cleanliness, rarely hosts — similar to Jawad on most dims
    (10, 4, 250, 450, 'night_owl',  'flexible', 'medium', 'rarely',    'english', '["affordable_rent","generator_coverage","wifi_quality"]'),
    -- Sarah: AUB, early bird, quiet, high cleanliness, never hosts — high standards
    (11, 1, 600, 900, 'early_bird', 'quiet',    'high',   'never',     'english', '["proximity_to_university","quiet_environment","cleanliness"]')
ON CONFLICT (user_id) DO NOTHING;

-- ─── LISTINGS ─────────────────────────────────────────────────────────────────
-- 50 listings across 8 Beirut neighbourhoods
-- Titles and descriptions mix Arabic, French, and English — BGE-M3 handles all three
-- Landlord 7 (scammer) has suspiciously cheap listings → used for fraud detection tests

INSERT INTO listings (landlord_id, neighbourhood_id, title, description, price, bedrooms, bathrooms, area_sqm, amenities, address, lat, lng, status) VALUES

-- ── HAMRA (neighbourhood_id = 1) — 8 listings ───────────────────────────────

(1, 1,
 'Studio قريب من AUB — الحمرا',
 'استوديو مفروش بالكامل، 5 دقائق سيراً من البوابة الرئيسية لـ AUB. كهرباء EDL 12 ساعة + مولد خاص 12 ساعة. إنترنت Touch Fiber 50Mbps. خزان مياه في المبنى — لا انقطاع. الإيجار يشمل الماء فقط.',
 480, 1, 1, 38,
 '{"furnished": true, "generator": true, "wifi": true, "ac": true, "water_tank": true, "water_included": true}',
 'Bliss Street, Hamra', 33.9009, 35.4763, 'active'),

(1, 1,
 '1BR Hamra | Bliss Street | ضوء طبيعي',
 'Apartment on a quiet side street, 10-min walk to AUB. Great natural light. Generator covers full electricity gap (12h EDL + 12h generator). Water cut Thursdays — building tank covers it. Landlord responds on WhatsApp within the hour.',
 550, 1, 1, 55,
 '{"furnished": true, "generator": true, "wifi": true, "water_tank": true, "washing_machine": true}',
 'Sadat Street, Hamra', 33.8978, 35.4812, 'active'),

(3, 1,
 'شقة غرفتين في الحمرا — مكيفة وجاهزة',
 'شقة فسيحة مؤلفة من غرفتين ومطبخ مجهز. مثالية لطالبين. المبنى عمره 5 سنوات، مولد كامل، موقف سيارات مدفوع. قريبة من LAU ومن سوبرماركت BouKhalil. الإيجار بدون فرش لكن المطبخ مجهز بالكامل.',
 720, 2, 1, 85,
 '{"furnished": false, "generator": true, "ac": true, "parking": true, "elevator": true, "water_tank": true}',
 'Makdessi Street, Hamra', 33.9001, 35.4779, 'active'),

(3, 1,
 'Studio Hamra — calme, lumineux, meublé',
 'Studio entièrement meublé dans une rue calme de Hamra. Cuisine équipée, AC, fibre optique incluse. Électricité EDL 12h + groupe électrogène privé (coût ~40$/mois en supplément). Immeuble propre, gardien 24h.',
 510, 1, 1, 42,
 '{"furnished": true, "generator": true, "wifi": true, "ac": true, "concierge": true}',
 'Jeanne d''Arc Street, Hamra', 33.8983, 35.4820, 'active'),

(4, 1,
 '3BR Student Flat | Hamra | Near LAU & AUB',
 'Spacious 3-bedroom apartment perfect for 3 students sharing. 2 bathrooms. 15-min walk to LAU Beirut, 20 min to AUB. Generator 24h (included in rent). Large living room with balcony. No furniture — bring your own or negotiate.',
 880, 3, 2, 110,
 '{"furnished": false, "generator": true, "balcony": true, "washing_machine": true, "elevator": true}',
 'Commodore Street, Hamra', 33.9005, 35.4795, 'active'),

(1, 1,
 'Spacious 1BR Hamra — Water Tank + Generator',
 'One-bedroom on the 4th floor (no elevator — good exercise!). Reliable generator covers the 12h EDL gap. Private water tank, never a dry day. Diesel heater available for winter (extra cost). Long-term tenants preferred.',
 560, 1, 1, 58,
 '{"furnished": true, "generator": true, "water_tank": true, "ac": true}',
 'Ras Beirut Street, Hamra', 33.8955, 35.4835, 'active'),

-- ⚠️ FRAUD BAIT — price impossibly low, vague description, urgency language
(7, 1,
 'FURNISHED STUDIO AUB AREA — URGENT RENT!!',
 'Beautiful fully furnished studio near AUB. Owner traveling abroad. Very clean. All bills included. Serious inquiries only. Send WhatsApp. Price negotiable. Available immediately.',
 150, 1, 1, 40,
 '{"furnished": true, "wifi": true, "bills_included": true}',
 'Hamra Area, Beirut', 33.8990, 35.4800, 'active'),

-- ⚠️ FRAUD BAIT — 2BR impossibly cheap, no address, contact outside platform
(7, 1,
 '2BR Apartment Hamra — Owner Abroad, Direct Deal',
 '2 bedroom apartment Hamra district. Owner currently outside Lebanon. Keys delivered after deposit. No agents. Contact via email only: owner.abroad.lb@gmail.com. Price is firm, no negotiation.',
 220, 2, 1, 80,
 '{"furnished": true}',
 'Hamra, Beirut', 33.8970, 35.4790, 'active'),

-- ── GEMMAYZEH (neighbourhood_id = 2) — 6 listings ───────────────────────────

(3, 2,
 'Studio Gemmayzeh — bâtiment historique, rénové',
 'Studio dans un immeuble pré-guerre magnifiquement restauré. Plafonds hauts, carreaux anciens, cuisine moderne. EDL 12h + groupe électrogène (40$/mois). Quartier très animé — idéal pour étudiants sociaux. Rue calme.',
 580, 1, 1, 50,
 '{"furnished": true, "generator": true, "wifi": true, "ac": true}',
 'Armenia Street, Gemmayzeh', 33.8930, 35.5133, 'active'),

(5, 2,
 '2BR Gemmayzeh | Terrasse Privée | Vue mer partielle',
 'Bel appartement 2 chambres avec terrasse privée et vue partielle sur mer. Immeuble avec groupe électrogène complet. Chauffe-eau solaire — économies sur le mazout. Quartier Gemmayzeh, ambiance unique. Non meublé.',
 820, 2, 1, 90,
 '{"furnished": false, "generator": true, "terrace": true, "sea_view": true, "solar_water_heater": true}',
 'Pasteur Street, Gemmayzeh', 33.8908, 35.5140, 'active'),

(1, 2,
 'شقة في الجميزة — قريبة من USJ وAUB',
 'شقة مريحة في الجميزة، مشياً من جامعة القديس يوسف (USJ) وقريبة من AUB. المبنى بكهرباء مولد 12 ساعة. الحي نشيط ومليء بالمقاهي والمطاعم. مناسبة لطالب يحب الحياة الاجتماعية.',
 460, 1, 1, 55,
 '{"furnished": true, "generator": true, "wifi": true}',
 'Huvelin Street, Gemmayzeh', 33.8940, 35.5128, 'active'),

(3, 2,
 'Artist Loft Gemmayzeh — Open Plan, High Ceilings',
 'Converted warehouse loft with exposed brick, iron beams, and 4.5m ceilings. No generator in building — bring your own UPS or plan around EDL 12h schedule. Best for creatives who work from home. Unfurnished.',
 650, 1, 1, 70,
 '{"furnished": false, "wifi": true, "ac": true}',
 'Gouraud Street, Gemmayzeh', 33.8922, 35.5155, 'active'),

(5, 2,
 'Compact Studio near Saint Joseph University',
 'Small but efficient studio 3 min walk from USJ main gate. Everything you need: AC, fast wifi, built-in wardrobes. Building generator covers full electricity gap. Quiet residential building, mostly professionals.',
 420, 1, 1, 36,
 '{"furnished": true, "generator": true, "wifi": true, "ac": true, "elevator": true}',
 'Huvelin Street, Gemmayzeh', 33.8895, 35.5115, 'active'),

(4, 2,
 '1BR Gemmayzeh | Historic Building | Fully Renovated',
 'Beautiful 1-bedroom in a restored pre-war building. New kitchen and bathroom, original tiled floors kept. Generator 12h in building. Gemmayzeh nightlife 2 min away — ear plugs provided! Landlord Mona is very responsive.',
 610, 1, 1, 62,
 '{"furnished": true, "generator": true, "wifi": true, "ac": true}',
 'Mar Mekhael Street, Gemmayzeh', 33.8925, 35.5162, 'active'),

-- ── ACHRAFIEH (neighbourhood_id = 3) — 7 listings ───────────────────────────

(6, 3,
 'Modern 1BR Achrafieh — 24h Security + Gym',
 'Premium building in Achrafieh with 24h concierge, gym, and full generator (one of the best EDL zones in Beirut — 18h/day). Near USJ and Haigazian. Ideal for a student who values security and comfort.',
 720, 1, 1, 65,
 '{"furnished": true, "generator": true, "gym": true, "security": true, "elevator": true, "wifi": true}',
 'Sursock Street, Achrafieh', 33.8901, 35.5148, 'active'),

(6, 3,
 'شقة 3 غرف أشرفية — مساحة واسعة ومريحة',
 'شقة عائلية فسيحة في الأشرفية، 3 غرف نوم ومطبخ كبير وصالون. مناسبة لـ 3 طلاب. الكهرباء EDL 18 ساعة يومياً (من أفضل المناطق في بيروت). غرفة خزن، مصعد، موقف سيارات مدفوع. بدون فرش.',
 1100, 3, 2, 130,
 '{"furnished": false, "generator": true, "storage": true, "parking": true, "elevator": true}',
 'Mar Nkoula, Achrafieh', 33.8892, 35.5139, 'active'),

(6, 3,
 'Studio Achrafieh — All Bills Included (Rare!)',
 'All-inclusive studio: rent covers electricity, water, internet, and generator. Fixed monthly cost — no surprises. Perfect for a student on a tight budget who hates dealing with bills. Near Sassine Square.',
 680, 1, 1, 40,
 '{"furnished": true, "generator": true, "wifi": true, "bills_included": true, "ac": true}',
 'Abdel Wahab El Inglizi, Achrafieh', 33.8865, 35.5120, 'active'),

(3, 3,
 'Classic 2BR Achrafieh — High Ceilings, Quiet Street',
 'Traditional Lebanese apartment with 3.5m ceilings, original mosaic floors, and large windows. 2 bedrooms, ideal for siblings or close friends. EDL 18h here — generator rarely needed. Quiet residential street.',
 820, 2, 1, 95,
 '{"furnished": false, "generator": true, "ac": true, "washing_machine": true}',
 'Sassine Square, Achrafieh', 33.8873, 35.5162, 'active'),

(4, 3,
 'Cozy 1BR Near USJ — 5 Min Walk',
 'One-bedroom apartment 5 min walk from USJ. Fully furnished with new appliances. Building has generator and water tank. Very quiet street — great for students who need to focus. Monthly rent includes water.',
 580, 1, 1, 58,
 '{"furnished": true, "generator": true, "wifi": true, "water_included": true, "water_tank": true}',
 'Huvelin Street, Achrafieh', 33.8895, 35.5042, 'active'),

(5, 3,
 'Executive Studio Achrafieh | Gym + Elevator',
 'Smart, compact studio in a modern building. Gym on ground floor, fast elevator, 24h security camera. EDL Achrafieh zone = 18h/day so generator cost is minimal (~15$/month). 10 min walk to USJ.',
 700, 1, 1, 46,
 '{"furnished": true, "generator": true, "gym": true, "elevator": true, "wifi": true, "security": true}',
 'Sioufi Street, Achrafieh', 33.8882, 35.5155, 'active'),

(6, 3,
 '2BR Achrafieh | Chauffe-eau solaire | Non meublé',
 'Grand appartement 2 chambres avec chauffe-eau solaire — économie de ~30$/mois sur le mazout en hiver. EDL 18h, groupe électrogène pour le reste. Immeuble récent, vue sur les toits de Beyrouth.',
 860, 2, 1, 92,
 '{"furnished": false, "generator": true, "solar_water_heater": true, "balcony": true, "elevator": true}',
 'Furn El Hayek, Achrafieh', 33.8871, 35.5143, 'active'),

-- ── MAR MIKHAEL (neighbourhood_id = 4) — 5 listings ────────────────────────

(5, 4,
 'Industrial Loft Mar Mikhael — Converted Warehouse',
 'High-ceiling loft conversion with exposed brick and original warehouse beams. Open plan living/sleeping/kitchen. Artsy Mar Mikhael neighbourhood — great coffee shops and galleries nearby. No elevator (ground floor). Generator 12h in building.',
 700, 1, 1, 70,
 '{"furnished": true, "wifi": true, "ac": true, "generator": true}',
 'Armenia Street, Mar Mikhael', 33.8860, 35.5195, 'active'),

(1, 4,
 'Modern Studio Mar Mikhael | New Building 2023',
 'Brand new building completed 2023. Smart entry lock, video intercom, generator included in service fees. EDL 12h + generator 12h = 24h power. 5 min walk to the port area and Mar Mikhael bars. Furnished.',
 520, 1, 1, 44,
 '{"furnished": true, "generator": true, "wifi": true, "elevator": true, "smart_lock": true}',
 'Charles Helou Avenue, Mar Mikhael', 33.8848, 35.5211, 'active'),

(3, 4,
 '2BR Mar Mikhael | Shared Rooftop Terrace',
 '2-bedroom apartment with access to shared rooftop terrace — BBQ area and city views. Ideal for 2 students. 2 bathrooms. Generator 12h. Note: Mar Mikhael is lively at night — light sleepers beware on weekends.',
 780, 2, 2, 88,
 '{"furnished": false, "generator": true, "terrace": true, "elevator": true}',
 'Pasteur Street, Mar Mikhael', 33.8872, 35.5180, 'active'),

(5, 4,
 'مار مخايل — غرفة وصالة — طابع تراثي',
 'شقة بطابع لبناني تراثي أصيل في مار مخايل. أرضيات بلاط قديمة، سقف عالٍ، نوافذ واسعة. الحي فني ونشيط. كهرباء EDL 12 ساعة + مولد 12 ساعة. المبنى بدون مصعد (الطابق الثالث).',
 590, 1, 1, 58,
 '{"furnished": true, "generator": true, "wifi": true, "ac": true}',
 'Electricite du Liban Street, Mar Mikhael', 33.8855, 35.5207, 'active'),

(4, 4,
 'مار مخايل — استوديو جديد | إنترنت سريع | مؤمَّن',
 'استوديو في مبنى حديث مع إنترنت فايبر سريع وكاميرات مراقبة. مولد كهرباء يغطي كامل انقطاع EDL. موقع ممتاز بالقرب من مطاعم ومقاهي مار مخايل. مفروش بالكامل.',
 540, 1, 1, 42,
 '{"furnished": true, "generator": true, "wifi": true, "security": true}',
 'Port Street, Mar Mikhael', 33.8845, 35.5225, 'active'),

-- ── VERDUN (neighbourhood_id = 5) — 5 listings ──────────────────────────────

(6, 5,
 'Luxury Studio Verdun — Generator 20h/day',
 'Verdun is one of Beirut''s top EDL zones — 20h electricity per day. This studio in a premium building adds a full private generator for the remaining 4h. Pool, gym, 24h security. Fully furnished with quality appliances.',
 750, 1, 1, 50,
 '{"furnished": true, "generator": true, "pool": true, "gym": true, "security": true, "elevator": true, "wifi": true}',
 'Verdun Street, Verdun', 33.8835, 35.4920, 'active'),

(6, 5,
 '1BR Verdun — High Floor | City View | Very Quiet',
 'High-floor apartment with panoramic city views and excellent sound insulation. Verdun 20h EDL — generator cost minimal (~20$/month). Close to Verdun mall and Hamra. Ideal for a student who needs quiet to study.',
 660, 1, 1, 65,
 '{"furnished": true, "generator": true, "wifi": true, "elevator": true, "city_view": true, "ac": true}',
 'Rachid Karame Street, Verdun', 33.8840, 35.4910, 'active'),

(6, 5,
 '2BR Verdun | Pool + Gym | Full Generator Coverage',
 'Spacious 2-bedroom in Verdun''s best residential building. Pool, gym, 24h concierge. Full generator — you will never lose power. 2 bathrooms. Not furnished but kitchen is fully equipped. Long-term contract preferred.',
 980, 2, 2, 100,
 '{"furnished": false, "generator": true, "pool": true, "gym": true, "concierge": true, "elevator": true}',
 'Maamari Street, Verdun', 33.8828, 35.4898, 'active'),

(4, 5,
 'Appartement 1BR Verdun — Calme et Lumineux',
 'Appartement 1 chambre très lumineux, au calme. Cuisine équipée, AC, chauffe-eau électrique. Verdun bénéficie de 20h EDL par jour — groupe électrogène rarement nécessaire (env. 20$/mois seulement). Proche des commerces.',
 620, 1, 1, 62,
 '{"furnished": true, "generator": true, "wifi": true, "ac": true}',
 'Damascus Road, Verdun', 33.8810, 35.4905, 'active'),

(5, 5,
 'Verdun | 3BR Penthouse | City & Sea Views',
 'Rare penthouse-level 3-bedroom with 360-degree views of Beirut and the Mediterranean. Top-floor — best breeze in summer. Generator 24h coverage. Private rooftop. Premium finishes throughout. Ideal for 3 serious students.',
 1350, 3, 2, 150,
 '{"furnished": false, "generator": true, "rooftop": true, "sea_view": true, "city_view": true, "elevator": true, "ac": true}',
 'Clemenceau Street, Verdun', 33.8845, 35.4930, 'active'),

-- ── BADARO (neighbourhood_id = 6) — 6 listings ──────────────────────────────

(1, 6,
 'Quiet 1BR Badaro — 10 Min to Downtown Beirut',
 'Well-maintained 1-bedroom on a very quiet residential street. 10-min taxi to downtown, 15 min to AUB. Generator 14h/day. Water tank in building. Neighbourhood feels safe and calm — great for focused studying.',
 540, 1, 1, 58,
 '{"furnished": true, "generator": true, "wifi": true, "water_tank": true}',
 'Badaro Street, Badaro', 33.8790, 35.5055, 'active'),

(1, 6,
 '2BR Badaro | Private Garden — نادر في بيروت',
 'Ground-floor apartment with a private walled garden — extremely rare in Beirut. 2 bedrooms, perfect for 2 students who want outdoor space. Generator 14h. Neighbourhood is quiet and residential. Unfurnished.',
 700, 2, 1, 90,
 '{"furnished": false, "generator": true, "garden": true, "water_tank": true}',
 'Abdallah El Mashnouq, Badaro', 33.8782, 35.5072, 'active'),

(5, 6,
 'Studio Badaro — Pet Friendly | Quiet Street',
 'One of the few pet-friendly studios in Beirut. Small garden access for dog walks. Generator 14h. Quiet street, kind neighbours. Close to Badaro cafes and the new bars on the strip. Furnished.',
 460, 1, 1, 40,
 '{"furnished": true, "generator": true, "pet_friendly": true, "garden": true, "wifi": true}',
 'Independence Street, Badaro', 33.8768, 35.5088, 'active'),

(3, 6,
 'Modern 1BR Badaro | New Kitchen + Full AC',
 'Fully renovated 1-bedroom with brand new kitchen appliances and split AC in every room. Building generator covers the 14h EDL gap in Badaro. Landlord Khalil is available on WhatsApp 7 days a week.',
 580, 1, 1, 60,
 '{"furnished": true, "generator": true, "wifi": true, "ac": true, "elevator": true}',
 'Souraya Street, Badaro', 33.8773, 35.5062, 'active'),

(4, 6,
 'بدارو — غرفة وصالة — هادئة — قرب المستشفى الجامعي',
 'شقة هادئة جداً في بدارو، قريبة من المستشفى الجامعي ومن وسط بيروت. مفروشة، مع مولد كهرباء 14 ساعة. مناسبة لطالب طب أو صيدلة. الجيران محترمون وهادئون.',
 420, 1, 1, 55,
 '{"furnished": true, "generator": true, "wifi": true, "ac": true}',
 'Clemenceau Street, Badaro', 33.8778, 35.5045, 'active'),

(5, 6,
 'Studio Badaro — Close to LIU & Downtown',
 'Affordable studio in Badaro, walking distance to LIU Beirut campus. Budget option — basic furniture, reliable generator. Good internet (Ogero fiber in the building). Best value-for-money in the area.',
 390, 1, 1, 38,
 '{"furnished": true, "generator": true, "wifi": true}',
 'Badaro Street, Badaro', 33.8785, 35.5065, 'active'),

-- ── RAS BEIRUT (neighbourhood_id = 7) — 7 listings ──────────────────────────

(4, 7,
 'Sea View Studio — Corniche Manara | بيروت',
 'استوديو مع إطلالة جزئية على البحر، خطوات من كورنيش المنارة. هواء بحري منعش يُغني عن التكييف صيفاً. كهرباء EDL 12 ساعة + مولد خاص. مناسب لطالب يحب المشي والبحر.',
 600, 1, 1, 45,
 '{"furnished": true, "generator": true, "wifi": true, "sea_view": true, "ac": true}',
 'Corniche Al Manara, Ras Beirut', 33.9000, 35.4713, 'active'),

(4, 7,
 '1BR Ras Beirut — Walking Distance to AUB',
 '1-bedroom apartment 15-min walk to AUB main gate. Quiet building, mostly AUB staff and students. Generator covers full electricity gap (12h). Landlord Mona lives in the same building — very fast maintenance response.',
 570, 1, 1, 56,
 '{"furnished": true, "generator": true, "wifi": true, "water_tank": true}',
 'Kantari Street, Ras Beirut', 33.8975, 35.4756, 'active'),

(3, 7,
 '2BR Ras Beirut | Full Sea View + Parking + 2 Bath',
 'Stunning unobstructed sea view from both bedrooms. 2 full bathrooms, dedicated parking space. Generator covers the 12h EDL gap. Premium location on Manara seafront. Unfurnished — bring your own character.',
 980, 2, 2, 100,
 '{"furnished": false, "generator": true, "sea_view": true, "parking": true, "elevator": true}',
 'Manara Street, Ras Beirut', 33.9015, 35.4690, 'active'),

(1, 7,
 'Budget Studio Ras Beirut — No Frills, Good Location',
 'Honestly basic studio — small, older building, no elevator (2nd floor). But: safe area, 20-min walk to AUB, generator 12h, and the cheapest option in Ras Beirut. Perfect for a student who just needs a clean place to sleep.',
 390, 1, 1, 35,
 '{"furnished": true, "generator": true}',
 'Omar Daouk Street, Ras Beirut', 33.8960, 35.4770, 'active'),

-- ⚠️ FRAUD BAIT — sea view 2BR impossibly cheap, urgency, off-platform contact
(7, 7,
 'SEA VIEW 2BR BEIRUT — OWNER TRAVELING — CALL NOW',
 'Luxury 2 bedroom apartment with full Mediterranean sea view. Owner relocating to Canada, must rent urgently. All furniture included. First month free. Send copy of passport and 2 months deposit by Western Union to secure. Very serious offers only.',
 280, 2, 1, 90,
 '{"furnished": true, "sea_view": true, "bills_included": true}',
 'Ras Beirut, Beirut', 33.8980, 35.4740, 'active'),

(3, 7,
 '3BR Ras Beirut — Ideal for 3 Students Sharing',
 '3-bedroom apartment designed for student sharing. Large living room, 2 bathrooms, big terrace. Generator 12h. Walking distance to AUB. Khalil manages 6 properties in Ras Beirut and Hamra — professional landlord, fast repairs.',
 950, 3, 2, 115,
 '{"furnished": false, "generator": true, "terrace": true, "elevator": true}',
 'Maamari Street, Ras Beirut', 33.8980, 35.4748, 'active'),

(4, 7,
 'شقة مفروشة رأس بيروت — قريبة من AUB والكورنيش',
 'شقة مفروشة بالكامل في منطقة رأس بيروت الهادئة، 15 دقيقة سيراً من AUB ومن الكورنيش. مولد كهرباء كامل. خزان مياه. الإيجار يشمل الإنترنت. مبنى هادئ ومحترم.',
 650, 1, 1, 60,
 '{"furnished": true, "generator": true, "wifi": true, "water_included": true, "water_tank": true}',
 'Kantari Street, Ras Beirut', 33.8972, 35.4745, 'active'),

-- ── DEKWANEH (neighbourhood_id = 8) — 6 listings ────────────────────────────

(1, 8,
 'Affordable 1BR Dekwaneh — Bus to Beirut Centre',
 'Budget 1-bedroom in Dekwaneh. Direct bus line to Beirut centre every 20 min. EDL only 8h/day here — building generator covers the rest (included in rent). Good option if you don''t mind the commute to save money.',
 350, 1, 1, 55,
 '{"furnished": true, "generator": true, "wifi": true}',
 'Dekwaneh Main Road', 33.8905, 35.5565, 'active'),

(3, 8,
 'Studio Dekwaneh | Small Gym | Budget Pick',
 'Compact studio in a newer Dekwaneh building with a small gym on the ground floor. EDL 8h here so generator is important — this building has one (included). Quiet area, mostly families and students from LIU.',
 320, 1, 1, 40,
 '{"furnished": true, "generator": true, "gym": true, "wifi": true}',
 'Haret Sakher Road, Dekwaneh', 33.8890, 35.5580, 'active'),

(3, 8,
 '2BR Dekwaneh — Near LIU Beirut Campus',
 '2-bedroom apartment 10 min walk from LIU Beirut. Good for 2 students sharing. Parking included. Note: Dekwaneh gets 8h EDL — generator is available but adds ~50$/month to costs. Unfurnished.',
 450, 2, 1, 88,
 '{"furnished": false, "generator": true, "parking": true, "storage": true}',
 'Fourn El Chebbak Road, Dekwaneh', 33.8870, 35.5555, 'active'),

(4, 8,
 'Appartement Dekwaneh — Calme, Rénové, Lumineux',
 'Appartement rénové dans une rue calme de Dekwaneh. Cuisine neuve, salle de bain moderne. EDL 8h/jour dans la région — groupe électrogène disponible (coût ~50$/mois à prévoir). Bon rapport qualité-prix.',
 380, 1, 1, 52,
 '{"furnished": true, "generator": true, "wifi": true, "ac": true}',
 'Nahr Street, Dekwaneh', 33.8880, 35.5590, 'active'),

-- ⚠️ FRAUD BAIT — all-inclusive studio impossibly cheap, no real address
(7, 8,
 'New Studio Dekwaneh — ALL INCLUSIVE $99/Month!!!',
 'Brand new studio apartment. Rent includes all bills, generator, wifi, water, and cleaning. Modern furniture. No deposit required. Available now. Contact landlord directly via WhatsApp: +961 XX XXX XXX. Limited offer.',
 99, 1, 1, 35,
 '{"furnished": true, "generator": true, "wifi": true, "bills_included": true}',
 'Dekwaneh, Lebanon', 33.8898, 35.5570, 'active'),

(5, 8,
 'Modern 1BR Dekwaneh | Value for Money',
 'Newer building in Dekwaneh with good finishes. 1 bedroom, separate kitchen and living area. Generator in building covers the 8h EDL gap (costs ~50$/month extra). Good transport links to Beirut — bus and service taxi available.',
 400, 1, 1, 58,
 '{"furnished": false, "generator": true, "wifi": true, "elevator": true}',
 'Dekwaneh Road', 33.8895, 35.5560, 'active');

-- ─── LISTING VERIFICATIONS ────────────────────────────────────────────────────
-- Legitimate landlords: phone verified and price in range
-- Scammer listings: not verified

INSERT INTO listing_verifications (listing_id, phone_verified, price_in_range)
SELECT id, true, true FROM listings WHERE landlord_id IN (1, 3, 4, 5, 6)
ON CONFLICT (listing_id) DO NOTHING;

INSERT INTO listing_verifications (listing_id, phone_verified, price_in_range)
SELECT id, false, false FROM listings WHERE landlord_id = 7
ON CONFLICT (listing_id) DO NOTHING;

-- ─── FRAUD REPORTS ────────────────────────────────────────────────────────────
-- Pre-seeded fraud scores for scammer listings — used by fraud module tests

INSERT INTO fraud_reports (listing_id, score, price_zscore, evidence) VALUES
(
    (SELECT id FROM listings WHERE title = 'FURNISHED STUDIO AUB AREA — URGENT RENT!!' LIMIT 1),
    0.92, -4.1,
    '{"price_flags": ["price_below_3_sigma", "price_too_low"], "text_flags": ["urgency_language", "contact_outside_platform"], "phone_flags": ["unverified_landlord"]}'
),
(
    (SELECT id FROM listings WHERE title = '2BR Apartment Hamra — Owner Abroad, Direct Deal' LIMIT 1),
    0.88, -3.8,
    '{"price_flags": ["price_below_3_sigma", "price_too_low"], "text_flags": ["owner_abroad_scam", "external_email_contact", "urgency_language"], "phone_flags": ["unverified_landlord"]}'
),
(
    (SELECT id FROM listings WHERE title = 'SEA VIEW 2BR BEIRUT — OWNER TRAVELING — CALL NOW' LIMIT 1),
    0.95, -4.5,
    '{"price_flags": ["price_below_3_sigma", "price_too_low"], "text_flags": ["owner_abroad_scam", "wire_transfer_request", "urgency_language", "passport_request"], "phone_flags": ["unverified_landlord"]}'
),
(
    (SELECT id FROM listings WHERE title = 'New Studio Dekwaneh — ALL INCLUSIVE $99/Month!!!' LIMIT 1),
    0.97, -5.2,
    '{"price_flags": ["price_below_3_sigma", "impossible_price"], "text_flags": ["no_deposit_scam", "urgency_language", "external_whatsapp_contact"], "phone_flags": ["unverified_landlord"]}'
)
ON CONFLICT DO NOTHING;

-- ─── LARA''S COMPLETE DEMO STORY ───────────────────────────────────────────────
-- Jawad (user_id=2) has a full journey: saved listings, roommate request,
-- agent conversation, and a landlord review — all 8 user stories are demonstrable

-- Jawad saves 3 listings
INSERT INTO saved_listings (user_id, listing_id)
SELECT 2, id FROM listings
WHERE title IN (
    'Studio قريب من AUB — الحمرا',
    '1BR Hamra | Bliss Street | ضوء طبيعي',
    'Studio Gemmayzeh — bâtiment historique, rénové'
)
ON CONFLICT (user_id, listing_id) DO NOTHING;

-- Jawad sends a roommate request to Karim (user_id=10)
-- They are similar on most dimensions (both night owls, rarely host guests)
-- making it a realistic high-score match
INSERT INTO roommate_requests (from_user_id, to_user_id, score, dimensions, status)
VALUES (
    2, 10,
    0.82,
    '{"sleep": 0.95, "study": 0.71, "cleanliness": 0.68, "guests": 0.90, "budget": 0.86}',
    'pending'
) ON CONFLICT DO NOTHING;

-- Jawad''s agent conversation history (Arabic + English — tests multilingual)
INSERT INTO agent_sessions (user_id, session_id, state, history, summary)
VALUES (
    2,
    'jawad-demo-session-001',
    '{"last_intent": "search_listings", "last_query": "studio near AUB under 600", "filters_applied": {"neighbourhood": "Hamra", "max_price": 600}}',
    '[
        {"role": "user", "content": "مرحبا، أبحث عن شقة قريبة من AUB بميزانية أقصاها 600 دولار"},
        {"role": "assistant", "content": "أهلاً لارا! وجدت 4 شقق ضمن ميزانيتك وقريبة من AUB. أفضلها: **Studio قريب من AUB** بـ480$/شهر — مفروش، مولد كامل، 5 دقائق مشياً من البوابة الرئيسية. هل تريدين مزيداً من التفاصيل؟"},
        {"role": "user", "content": "What are the generator hours like in Hamra?"},
        {"role": "assistant", "content": "Hamra gets about **12 hours of EDL electricity per day**. Most buildings have a private generator that covers the remaining 12 hours, typically costing 35–45 USD/month extra. The studio I recommended includes the generator in the rent — no surprise bills."},
        {"role": "user", "content": "هل في مياه منقطعة؟"},
        {"role": "assistant", "content": "نعم، في الحمرا عادةً يُقطع الماء يوم الخميس. لكن الاستوديو الذي أنصحكِ به يملك خزان مياه في المبنى، لذا لن تتأثري بالانقطاع. هذه تفصيلة مهمة جداً يجب التحقق منها قبل التوقيع."}
    ]',
    'Jawad searched for studios near AUB under $600. Recommended the Hamra studio at $480. Answered questions about generator hours (12h EDL + 12h generator) and water supply (Thursday cuts, building has tank).'
) ON CONFLICT (session_id) DO NOTHING;

-- Jawad reviews landlord 1 (demo landlord) based on the studio listing
INSERT INTO landlord_reviews (landlord_id, reviewer_id, listing_id, maintenance, responsiveness, honesty, hidden_fees, ai_summary)
SELECT
    1, 2, listings.id,
    4, 5, 4, 4,
    'Responsive landlord who answers WhatsApp quickly. Maintenance was handled within 48 hours. One minor issue: generator cost was slightly higher than quoted (~5$/month extra). Overall a trustworthy and professional landlord.'
FROM listings WHERE title = 'Studio قريب من AUB — الحمرا' LIMIT 1
ON CONFLICT (landlord_id, reviewer_id, listing_id) DO NOTHING;

-- Jawad''s notifications
INSERT INTO notifications (user_id, type, payload, read) VALUES
    (2, 'roommate_request_sent',
     '{"to_user": "karim@demo.com", "match_score": 0.82, "top_dimension": "sleep"}',
     false),
    (2, 'new_roommate_match',
     '{"matched_user": "karim@demo.com", "score": 0.82, "message": "You and Karim are highly compatible on sleep schedule and guest preferences."}',
     false),
    (2, 'listing_price_drop',
     '{"listing_title": "1BR Hamra | Bliss Street | ضوء طبيعي", "old_price": 600, "new_price": 550}',
     true)
ON CONFLICT DO NOTHING;

-- Omar''s notification (received Jawad''s roommate request... wait, she sent it to Karim)
-- Karim receives the roommate request notification
INSERT INTO notifications (user_id, type, payload, read) VALUES
    (10, 'roommate_request_received',
     '{"from_user": "jawad@demo.com", "match_score": 0.82, "message": "Jawad thinks you would be a great roommate match!"}',
     false)
ON CONFLICT DO NOTHING;
