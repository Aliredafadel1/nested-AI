-- NestAI Demo Reset — restores Jawad (user_id=2) to her original demo state
-- Run before each demo session: docker compose exec db psql -U nestai -d nestai -f /seed/reset_demo.sql

-- Remove mutable demo data for Jawad and the students who interact with her
DELETE FROM notifications        WHERE user_id IN (2, 10);
DELETE FROM roommate_requests    WHERE from_user_id = 2 OR to_user_id = 2;
DELETE FROM saved_listings       WHERE user_id = 2;
DELETE FROM agent_sessions       WHERE user_id = 2;
DELETE FROM landlord_reviews     WHERE reviewer_id = 2;

-- Restore saved listings
INSERT INTO saved_listings (user_id, listing_id)
SELECT 2, id FROM listings
WHERE title IN (
    'Studio قريب من AUB — الحمرا',
    '1BR Hamra | Bliss Street | ضوء طبيعي',
    'Studio Gemmayzeh — bâtiment historique, rénové'
)
ON CONFLICT (user_id, listing_id) DO NOTHING;

-- Restore roommate request to Karim
INSERT INTO roommate_requests (from_user_id, to_user_id, score, dimensions, status)
VALUES (
    2, 10, 0.82,
    '{"sleep": 0.95, "study": 0.71, "cleanliness": 0.68, "guests": 0.90, "budget": 0.86}',
    'pending'
) ON CONFLICT DO NOTHING;

-- Restore agent session
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
        {"role": "assistant", "content": "نعم، في الحمرا عادةً يُقطع الماء يوم الخميس. لكن الاستوديو الذي أنصحكِ به يملك خزان مياه في المبنى، لذا لن تتأثري بالانقطاع."}
    ]',
    'Jawad searched for studios near AUB under $600. Recommended the Hamra studio at $480. Answered questions about generator hours and water supply.'
) ON CONFLICT (session_id) DO NOTHING;

-- Restore landlord review
INSERT INTO landlord_reviews (landlord_id, reviewer_id, listing_id, maintenance, responsiveness, honesty, hidden_fees, ai_summary)
SELECT
    1, 2, listings.id,
    4, 5, 4, 4,
    'Responsive landlord who answers WhatsApp quickly. Maintenance was handled within 48 hours. Overall a trustworthy and professional landlord.'
FROM listings WHERE title = 'Studio قريب من AUB — الحمرا' LIMIT 1
ON CONFLICT (landlord_id, reviewer_id, listing_id) DO NOTHING;

-- Restore notifications
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

INSERT INTO notifications (user_id, type, payload, read) VALUES
    (10, 'roommate_request_received',
     '{"from_user": "jawad@demo.com", "match_score": 0.82, "message": "Jawad thinks you would be a great roommate match!"}',
     false)
ON CONFLICT DO NOTHING;

SELECT 'Demo reset complete — Jawad is ready.' AS status;
