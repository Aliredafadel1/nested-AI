-- RAG chunks: Lebanon housing survival FAQs
-- source_type = 'housing_faq'
-- embedding column populated by seed_rag_embeddings Celery task after insert

INSERT INTO rag_chunks (source_type, source_id, chunk_text, language) VALUES

-- Generator companies by neighbourhood
('housing_faq', NULL, 'In Hamra, the main private generator subscriptions are provided by local generator owners (ashab muwallidat). Common providers include Hamra Electric and neighbourhood co-ops. Monthly subscriptions range from 35–50 USD for 8–12 amperes. Ask your building concierge (bawwab) for the neighbourhood generator contact.', 'en'),
('housing_faq', NULL, 'في الحمرا، يمكن الحصول على اشتراك مولّد خاص من خلال أصحاب المولدات في الحي. الأسعار الشائعة تتراوح بين 35 و50 دولاراً شهرياً مقابل 8 إلى 12 أمبير. تواصل مع بواب البناء للحصول على معلومات المولد في حيّك.', 'ar'),
('housing_faq', NULL, 'In Gemmayzeh and Mar Mikhael, generator subscriptions typically cost 40–55 USD per month for standard residential amperage (8A). The area has frequent EDL cuts — averaging 12 hours/day — so a generator subscription is essential. Subscriptions are arranged directly with the building landlord or local generator operator.', 'en'),
('housing_faq', NULL, 'Achrafieh benefits from one of the best EDL schedules in Beirut at roughly 18 hours/day. Generator costs here are lower (25–35 USD/month) due to less reliance. Major residential buildings in Achrafieh often have their own building generators managed by the syndic.', 'en'),
('housing_faq', NULL, 'Verdun has Beirut''s best EDL hours (up to 20h/day) and the lowest generator costs (20–25 USD/month). Generator subscriptions in Verdun are arranged through building management companies that operate centralised generators for the residential towers.', 'en'),
('housing_faq', NULL, 'In Dekwaneh (outer suburb), EDL hours are among the lowest in Greater Beirut (around 8h/day). Expect generator costs of 45–60 USD/month. Many buildings rely heavily on private generators — confirm amperage and cost before signing a lease.', 'en'),
('housing_faq', NULL, 'Badaro generator subscriptions average 35–45 USD/month for 8A. The area gets roughly 14 EDL hours/day. Most residential buildings have individual generator contracts; ask the landlord for the generator owner''s number before moving in.', 'en'),
('housing_faq', NULL, 'Ras Beirut (near AUB) generator subscriptions cost 38–50 USD/month. The area averages 12 EDL hours. Several student-oriented buildings near AUB include generator cost in the rent — always confirm whether it is included or separate.', 'en'),

-- Water delivery services
('housing_faq', NULL, 'Tap water in Lebanon is not safe to drink. Most Beirut residents use either water cooler subscriptions (with 19-litre gallons) or water delivery trucks (tankers). A 19-litre gallon costs around 1.5–3 USD from supermarkets or water stations. Monthly water costs for a student averages 15 USD.', 'en'),
('housing_faq', NULL, 'المياه في لبنان غير صالحة للشرب من الصنبور. يعتمد السكان على قوارير المياه (جالونات 19 لتراً) بسعر 1.5–3 دولار، أو صهاريج مياه للمنازل الكبيرة. التكلفة الشهرية لطالب جامعي تتراوح بين 10 و20 دولاراً.', 'ar'),
('housing_faq', NULL, 'Water tanker delivery is available across Beirut for filling rooftop tanks. Tanker companies typically charge by cubic metre. For individual apartments, buying 19-litre water gallons from local stores (dukkan) or delivery services like "Tannourine" or "Sohat" is more practical. Many supermarkets offer free delivery for orders over 2 gallons.', 'en'),
('housing_faq', NULL, 'In student-heavy areas like Hamra and Ras Beirut, several water delivery apps and WhatsApp groups coordinate water gallon orders. Average cost: 2 USD per 19L gallon. A student typically uses 2–3 gallons per week for drinking and cooking.', 'en'),

-- 24h pharmacies by area
('housing_faq', NULL, 'In Hamra, several pharmacies operate on a 24-hour rotating schedule. Pharmacie Hamra (near the old Hamra Cinema) and Pharmacie Rizk are well-known. The Lebanese Order of Pharmacists posts the nightly duty pharmacy schedule at pharmacy entrances. Call 1214 for the duty pharmacy hotline.', 'en'),
('housing_faq', NULL, 'للصيدليات المناوبة في لبنان (24 ساعة)، يمكن الاتصال بالرقم 1214 أو الاستعلام في أقرب صيدلية عن الصيدلية المناوبة في حيّك. في الحمرا وعين المريسة توجد صيدليات مناوبة على مدار الساعة في معظم الليالي.', 'ar'),
('housing_faq', NULL, 'In Achrafieh and Gemmayzeh, Pharmacie Sassine and several others near Sassine Square operate late hours or 24h rotationally. Pharmacie Sodeco is another reliable option. The rotating schedule is posted on the pharmacy door or call 1214.', 'en'),
('housing_faq', NULL, 'Near AUB (Ras Beirut), the AUB Medical Center pharmacy operates extended hours for emergencies. The Bliss Street pharmacies (Bliss Pharmacy, AUB area) are open until at least midnight daily. For true 24h service, check the duty pharmacy rotation via the 1214 hotline.', 'en'),

-- EDL power schedule information
('housing_faq', NULL, 'EDL (Électricité du Liban) power cuts vary dramatically by neighbourhood in Beirut. The schedule changes seasonally and without notice. Verdun and parts of Achrafieh receive the best EDL service (18–20h/day). Hamra, Gemmayzeh, Mar Mikhael, and Ras Beirut receive roughly 12h/day. Dekwaneh and outer suburbs may receive only 6–8h/day.', 'en'),
('housing_faq', NULL, 'يتفاوت جدول انقطاع الكهرباء (EDL) بحسب المنطقة. فردان والأشرفية تحصل على أفضل خدمة (18–20 ساعة يومياً). الحمرا والجميزة تحصل على نحو 12 ساعة. الدكوانة والضواحي الخارجية قد تحصل على 6–8 ساعات فقط. يُعوَّض الباقي بالمولدات الخاصة.', 'ar'),
('housing_faq', NULL, 'To find out your specific EDL cut schedule, ask your building concierge or neighbours — they will know the local pattern. The schedule is rarely published officially. EDL Lebanon has a hotline at 1620 for outage reports. Apps like "EDL Lebanon" on mobile may show approximate schedules for major areas.', 'en'),
('housing_faq', NULL, 'When calculating your monthly electricity cost in Lebanon, add both the EDL bill (if any) and the private generator subscription. In 2024–2025, EDL bills are often low or zero due to subsidised rates, but generator bills are the real expense. Budget 30–60 USD/month total for electricity depending on your neighbourhood and usage.', 'en'),

-- Internet providers (Ogero, WT, IDM)
('housing_faq', NULL, 'Lebanon''s main internet providers are Ogero (state DSL), IDM (private), and WT (wireless/WiMAX). Ogero DSL requires a landline and is available in most Beirut areas — speeds vary 4–20 Mbps depending on the copper line quality. Monthly DSL plans from Ogero cost around 25–40 USD for 50GB–unlimited plans.', 'en'),
('housing_faq', NULL, 'IDM (Internet Data Management) is a popular private ISP offering fibre and DSL packages. IDM is faster and more reliable than Ogero in many areas. Plans range from 30–60 USD/month for 50Mbps fibre. Coverage is strongest in central Beirut (Hamra, Achrafieh, Verdun, Ras Beirut).', 'en'),
('housing_faq', NULL, 'WT (Wireless Telecom) offers WiMAX wireless internet — useful where DSL infrastructure is poor. Plans cost 25–50 USD/month. WT works well in outer suburbs like Dekwaneh where Ogero DSL quality is poor. Installation is quick (no landline needed). Ask the landlord which ISP works best in the building before signing.', 'en'),
('housing_faq', NULL, 'مزودو خدمة الإنترنت الرئيسيون في لبنان: أوجيرو (DSL حكومي)، IDM (خاص، ألياف ضوئية)، وWT (لاسلكي). أسعار الاشتراك الشهري تتراوح بين 25 و60 دولاراً. اسأل المالك أو جيرانك عن أفضل مزوّد في المبنى قبل الاشتراك.', 'ar'),
('housing_faq', NULL, 'For students near AUB or LAU Beirut campuses, AUB offers campus Wi-Fi accessible from nearby off-campus apartments via VPN or eduroam if your university participates. This can supplement home internet. However, for reliable home use, subscribing to IDM or Ogero is recommended.', 'en'),
('housing_faq', NULL, 'Internet outages are common in Lebanon due to power cuts and infrastructure issues. Most routers lose connection when EDL cuts occur unless on UPS backup. A 4G SIM card (Alfa or Touch) as a mobile hotspot backup is a common strategy among students. 4G data plans cost around 10–25 USD/month for 20–50GB.', 'en')

ON CONFLICT DO NOTHING;
