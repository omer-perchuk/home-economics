--
-- PostgreSQL database dump
--

\restrict iC5LUrLtzun0tJlkcJWNEZSgg40UEZgroGaCwVVWcJ0gBdvNJUAXHSnVXeBmnoq

-- Dumped from database version 18.3 (Debian 18.3-1.pgdg12+1)
-- Dumped by pg_dump version 18.3

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: public; Type: SCHEMA; Schema: -; Owner: homeeconomics_user
--

-- *not* creating schema, since initdb creates it


ALTER SCHEMA public OWNER TO homeeconomics_user;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: families; Type: TABLE; Schema: public; Owner: homeeconomics_user
--

CREATE TABLE public.families (
    id integer NOT NULL,
    name character varying NOT NULL,
    twilio_whatsapp_number character varying,
    created_at timestamp without time zone,
    dashboard_title text DEFAULT 'Home Budget'::text NOT NULL
);


ALTER TABLE public.families OWNER TO homeeconomics_user;

--
-- Name: families_id_seq; Type: SEQUENCE; Schema: public; Owner: homeeconomics_user
--

CREATE SEQUENCE public.families_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.families_id_seq OWNER TO homeeconomics_user;

--
-- Name: families_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: homeeconomics_user
--

ALTER SEQUENCE public.families_id_seq OWNED BY public.families.id;


--
-- Name: transactions; Type: TABLE; Schema: public; Owner: homeeconomics_user
--

CREATE TABLE public.transactions (
    id integer NOT NULL,
    original_text character varying,
    description character varying NOT NULL,
    amount double precision NOT NULL,
    type character varying NOT NULL,
    category character varying NOT NULL,
    family_id integer NOT NULL,
    user_id integer,
    user_phone character varying,
    created_at timestamp without time zone
);


ALTER TABLE public.transactions OWNER TO homeeconomics_user;

--
-- Name: transactions_id_seq; Type: SEQUENCE; Schema: public; Owner: homeeconomics_user
--

CREATE SEQUENCE public.transactions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.transactions_id_seq OWNER TO homeeconomics_user;

--
-- Name: transactions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: homeeconomics_user
--

ALTER SEQUENCE public.transactions_id_seq OWNED BY public.transactions.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: homeeconomics_user
--

CREATE TABLE public.users (
    id integer NOT NULL,
    name character varying NOT NULL,
    phone character varying NOT NULL,
    family_id integer NOT NULL,
    created_at timestamp without time zone
);


ALTER TABLE public.users OWNER TO homeeconomics_user;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: homeeconomics_user
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_seq OWNER TO homeeconomics_user;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: homeeconomics_user
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: families id; Type: DEFAULT; Schema: public; Owner: homeeconomics_user
--

ALTER TABLE ONLY public.families ALTER COLUMN id SET DEFAULT nextval('public.families_id_seq'::regclass);


--
-- Name: transactions id; Type: DEFAULT; Schema: public; Owner: homeeconomics_user
--

ALTER TABLE ONLY public.transactions ALTER COLUMN id SET DEFAULT nextval('public.transactions_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: homeeconomics_user
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Data for Name: families; Type: TABLE DATA; Schema: public; Owner: homeeconomics_user
--

COPY public.families (id, name, twilio_whatsapp_number, created_at, dashboard_title) FROM stdin;
1	משפחת עומר	whatsapp:+14155238886	2026-03-09 20:20:16.524924	האני והאני בדרך למיליון
\.


--
-- Data for Name: transactions; Type: TABLE DATA; Schema: public; Owner: homeeconomics_user
--

COPY public.transactions (id, original_text, description, amount, type, category, family_id, user_id, user_phone, created_at) FROM stdin;
14	65 ש״ח פיצה	ש״ח פיצה	65	expense	אוכל בחוץ וקפה	1	1	whatsapp:+972536278656	2026-02-01 00:00:00
15	1400 שכ״ד	שכ״ד	1400	expense	אחר	1	1	whatsapp:+972536278656	2026-02-19 00:00:00
16	ארנונה ינואר פברואר 663 ש״ח	ארנונה ינואר פ רואר  ש״ח	663	expense	דיור וחשבונות	1	1	whatsapp:+972536278656	2026-02-19 00:00:00
17	55 ש״ח מכבי חיפה	ש״ח מכ י חיפה	55	expense	אחר	1	1	whatsapp:+972536278656	2026-02-19 00:00:00
18	75 ש״ח חיפה - סכנין	ש״ח חיפה - סכנין	75	expense	אחר	1	1	whatsapp:+972536278656	2026-02-19 00:00:00
48	53 ש״ח אפל	ש״ח אפל	53	expense	בילויים ופנאי	1	1	whatsapp:+972536278656	2026-03-19 00:00:00
46	83 ש״ח סופר פארם	ש״ח סופר פארם	83	expense	בריאות ופארם	1	1	whatsapp:+972536278656	2026-03-19 00:00:00
21	876 שח מרכזה	שח מרכזה	876	expense	סופר וקניות לבית	1	1	whatsapp:+972536278656	2026-02-19 00:00:00
22	620 יום הולדת סרגיי	יום הולדת סרגיי	620	expense	אחר	1	1	whatsapp:+972536278656	2026-02-19 00:00:00
50	55 ש״ח kfc	ש״ח kfc	55	expense	אוכל בחוץ וקפה	1	1	whatsapp:+972536278656	2026-03-19 00:00:00
57	70 חומבו	חומבו	70	expense	סופר וקניות לבית	1	1	whatsapp:+972536278656	2026-03-19 00:00:00
25	75 ש״ח חיפה - פ״ת	ש״ח חיפה - פ״ת	75	expense	בילויים ופנאי	1	1	whatsapp:+972536278656	2026-02-19 00:00:00
26	45 ש״ח תרופות בסופר פארם	ש״ח תרופות  סופר פארם	45	expense	בריאות ופארם	1	1	whatsapp:+972536278656	2026-02-19 00:00:00
27	100 ש״ח תרופות	ש״ח תרופות	100	expense	בריאות ופארם	1	1	whatsapp:+972536278656	2026-02-19 00:00:00
28	250 ש״ח קניות	ש״ח קניות	250	expense	סופר וקניות לבית	1	1	whatsapp:+972536278656	2026-02-19 00:00:00
29	63 שח זול סטוק	שח זול סטוק	63	expense	אחר	1	1	whatsapp:+972536278656	2026-02-19 00:00:00
30	110 ש״ח קניות	ש״ח קניות	110	expense	סופר וקניות לבית	1	1	whatsapp:+972536278656	2026-02-19 00:00:00
31	400 ש״ח טסט לבובה	ש״ח טסט ל ו ה	400	expense	תחבורה	1	1	whatsapp:+972536278656	2026-02-19 00:00:00
32	62 ש״ח מקדונלדס	ש״ח מקדונלדס	62	expense	אוכל בחוץ וקפה	1	1	whatsapp:+972536278656	2026-02-19 00:00:00
33	700 ש״ח הליכון	ש״ח הליכון	700	expense	בילויים ופנאי	1	1	whatsapp:+972536278656	2026-02-19 00:00:00
34	55 ש״ח קניות לעוגה	ש״ח קניות לעוגה	55	expense	סופר וקניות לבית	1	1	whatsapp:+972536278656	2026-02-19 00:00:00
35	20 שח מיננה	שח מיננה	20	expense	אחר	1	1	whatsapp:+972536278656	2026-02-19 00:00:00
36	221 ש״ח אוכל סולט	ש״ח אוכל סולט	221	expense	אוכל בחוץ וקפה	1	1	whatsapp:+972536278656	2026-02-19 00:00:00
37	160 ש״ח שווארמה וגולדה	ש״ח שווארמה וגולדה	160	expense	אוכל בחוץ וקפה	1	1	whatsapp:+972536278656	2026-02-19 00:00:00
38	55 ש״ח חיפה ק״ש	ש״ח חיפה ק״ש	55	expense	בילויים ופנאי	1	1	whatsapp:+972536278656	2026-02-19 00:00:00
39	1694 ביטוח חובה	יטוח חו ה	1694	expense	תחבורה	1	1	whatsapp:+972536278656	2026-02-19 00:00:00
40	2466 ביטוח מקיף	יטוח מקיף	2466	expense	תחבורה	1	1	whatsapp:+972536278656	2026-02-19 00:00:00
41	150 מקדונלדס	מקדונלדס	150	expense	אוכל בחוץ וקפה	1	1	whatsapp:+972536278656	2026-02-19 00:00:00
42	45 הדפסות	הדפסות	45	expense	אחר	1	1	whatsapp:+972536278656	2026-02-19 00:00:00
43	80 עלי אקספרס	י אקספרס	80	expense	בילויים ופנאי	1	1	whatsapp:+972536278656	2026-02-19 00:00:00
44	1086 רישיון רכב	רישיון רכ	1086	expense	תחבורה	1	1	whatsapp:+972536278656	2026-02-19 00:00:00
19	65 ש״ח גלידות	ש״ח גלידות	65	expense	אוכל בחוץ וקפה	1	1	whatsapp:+972536278656	2026-02-19 00:00:00
20	242 שח בלוברי	שח  בלוברי	242	expense	בילויים ופנאי	1	1	whatsapp:+972536278656	2026-02-19 00:00:00
23	140 שח איפור	שח איפור	140	expense	בריאות ופארם	1	1	whatsapp:+972536278656	2026-02-19 00:00:00
24	עלי אקספרס 50 שח	עלי אקספרס	50	expense	בילויים ופנאי	1	1	whatsapp:+972536278656	2026-02-19 00:00:00
45	27 ש״ח קניות	ש״ח קניות	27	expense	סופר וקניות לבית	1	1	whatsapp:+972536278656	2026-03-19 15:45:31.401728
47	960 ש״ח קניות	ש״ח קניות	960	expense	סופר וקניות לבית	1	1	whatsapp:+972536278656	2026-03-19 15:45:33.015896
49	דלק פברואר 704 שח	דלק פ רואר  שח	704	expense	תחבורה	1	1	whatsapp:+972536278656	2026-03-19 15:45:34.23448
52	מקדונלדס 20 ש״ח	מקדונלדס  ש״ח	20	expense	אוכל בחוץ וקפה	1	1	whatsapp:+972536278656	2026-03-19 15:45:35.666511
53	דלק סונול 255 ש״ח	דלק סונול  ש״ח	255	expense	תחבורה	1	1	whatsapp:+972536278656	2026-03-19 15:45:36.125849
55	63 ש״ח ארומה	ש״ח ארומה	63	expense	אוכל בחוץ וקפה	1	1	whatsapp:+972536278656	2026-03-19 15:45:37.183523
56	350 ש״ח הטענה בהסתדרות	ש״ח הטענה  הסתדרות	350	expense	אחר	1	1	whatsapp:+972536278656	2026-03-19 15:45:37.938793
54	בגדים וללין בהצדעה - 425 ש״ח	בגדים וללין בהצדעה	425	expense	אחר	1	1	whatsapp:+972536278656	2026-03-19 00:00:00
51	130 ש״ח רנואר	ש״ח רנואר	130	expense	ביגוד והנעלה	1	1	whatsapp:+972536278656	2026-03-19 00:00:00
65	גז ינואר פברואר 136	גז ינואר פ רואר	136	expense	דיור וחשבונות	1	1	whatsapp:+972536278656	2026-03-19 15:45:56.65628
68	40 חומרי ניקוי	חומרי ניקוי	40	expense	סופר וקניות לבית	1	1	whatsapp:+972536278656	2026-03-19 00:00:00
71	60 באבלתי	באבלתי	60	expense	אוכל בחוץ וקפה	1	1	whatsapp:+972536278656	2026-03-19 00:00:00
74	90 h&m	h&m	90	expense	ביגוד והנעלה	1	1	whatsapp:+972536278656	2026-03-19 00:00:00
60	45 הדפסות	הדפסות	45	expense	אחר	1	1	whatsapp:+972536278656	2026-03-19 15:45:53.61061
63	חשמל ינואר פברואר 818	חשמל ינואר פ רואר	818	expense	דיור וחשבונות	1	1	whatsapp:+972536278656	2026-03-19 15:45:55.168448
72	150 מקדונלדס	מקדונלדס	150	expense	אוכל בחוץ וקפה	1	1	whatsapp:+972536278656	2026-03-19 15:46:01.022439
69	65 מתוק	מתוק	65	expense	אוכל בחוץ וקפה	1	1	whatsapp:+972536278656	2026-03-19 00:00:00
66	ביטוח חיים יול 150	יטוח חיים יול	150	expense	בריאות ופארם	1	1	whatsapp:+972536278656	2026-03-19 00:00:00
61	80 עלי אקספרס	י אקספרס	80	expense	אחר	1	1	whatsapp:+972536278656	2026-03-19 15:45:54.039597
75	16 קפה	קפה	16	expense	אוכל בחוץ וקפה	1	1	whatsapp:+972536278656	2026-03-19 15:46:44.659328
76	90 מקדונלדס	מקדונלדס	90	expense	אוכל בחוץ וקפה	1	1	whatsapp:+972536278656	2026-03-19 15:47:20.426396
67	ביטוח בריאות יול 108	יטוח  ריאות יול	108	expense	בריאות ופארם	1	1	whatsapp:+972536278656	2026-03-19 00:00:00
70	80 גוזיה	 ביגוד גוזיה	80	expense	אחר	1	1	whatsapp:+972536278656	2026-03-19 00:00:00
77	סופר דבאח 520	סופר ד אח	520	expense	סופר וקניות לבית	1	1	whatsapp:+972536278656	2026-03-19 16:34:09.111587
78	54 שיננית	שיננית	54	expense	בריאות ופארם	1	2	whatsapp:+972546216377	2026-03-20 00:00:00
79	מקדונלדס 5	מקדונלדס	5	expense	אוכל בחוץ וקפה	1	1	whatsapp:+972536278656	2026-03-22 16:16:49.610151
80	265 ש״ח סופר יוניברס	ש״ח סופר יוני רס	265	expense	סופר וקניות לבית	1	1	whatsapp:+972536278656	2026-03-22 17:07:54.965335
91	123 אוכל בחוץ	מרכזה	123	expense	אוכל בחוץ וקפה	1	2	whatsapp:+972546216377	2026-03-24 00:00:00
92	60 עלי אקספרס	עלי אקספרס	60	expense	אחר	1	1	whatsapp:+972536278656	2026-03-24 18:23:23.230822
93	1400 שכר דירה מרץ	שכר דירה מרץ	1400	expense	דיור וחשבונות	1	1	whatsapp:+972536278656	2026-03-25 13:54:43.512263
90	304 בגדים אדיקט	בגדים אדיקט	304	expense	ביגוד והנעלה	1	2	whatsapp:+972546216377	2026-03-24 00:00:00
73	540 זארה	זארה	540	expense	ביגוד והנעלה	1	1	whatsapp:+972536278656	2026-03-19 00:00:00
81	35 ש״ח openai	ש״ח openai	35	expense	בילויים ופנאי	1	1	whatsapp:+972536278656	2026-03-23 00:00:00
94	42 סופר רודיס	סופר רודיס	42	expense	סופר וקניות לבית	1	1	whatsapp:+972536278656	2026-03-26 20:15:48.903651
95	35 ksp	ksp	35	expense	בריאות ופארם	1	2	whatsapp:+972546216377	2026-03-27 00:00:00
96	78 מים	מים	78	expense	דיור וחשבונות	1	2	whatsapp:+972546216377	2026-03-27 18:48:50.841941
97	פנגו 11	פנגו 11	11	expense	תחבורה	1	1	whatsapp:+972536278656	2026-03-27 18:49:29.796996
64	מים ינואר פברואר 181	מים ינואר פ רואר	181	expense	דיור וחשבונות	1	1	whatsapp:+972536278656	2026-02-19 00:00:00
98	אפל חשבון ומיוזיק	אפל חשבון ומיוזיק	60	expense	בילויים ופנאי	1	\N	\N	2026-03-01 00:00:00
99	195 שווארמה	שווארמה	195	expense	אוכל בחוץ וקפה	1	1	whatsapp:+972536278656	2026-03-30 21:48:30.759731
100	85 קניות סופר	קניות סופר	85	expense	סופר וקניות לבית	1	1	whatsapp:+972536278656	2026-03-31 16:17:03.810163
102	90 מתנה קרם ברולה	מתנה קרם ברולה	90	expense	מתנות ותרומות	1	1	whatsapp:+972536278656	2026-04-02 10:21:24.965194
104	200 זארה	זארה	200	expense	ביגוד והנעלה	1	1	whatsapp:+972536278656	2026-04-02 10:23:46.453189
105	237 סופר	סופר	237	expense	סופר וקניות לבית	1	1	whatsapp:+972536278656	2026-04-02 10:23:58.479839
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: homeeconomics_user
--

COPY public.users (id, name, phone, family_id, created_at) FROM stdin;
1	עומר	whatsapp:+972536278656	1	2026-03-09 20:20:16.605961
2	יוליה	whatsapp:+972546216377	1	2026-03-09 20:20:16.605965
\.


--
-- Name: families_id_seq; Type: SEQUENCE SET; Schema: public; Owner: homeeconomics_user
--

SELECT pg_catalog.setval('public.families_id_seq', 2, true);


--
-- Name: transactions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: homeeconomics_user
--

SELECT pg_catalog.setval('public.transactions_id_seq', 108, true);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: homeeconomics_user
--

SELECT pg_catalog.setval('public.users_id_seq', 4, true);


--
-- Name: families families_name_key; Type: CONSTRAINT; Schema: public; Owner: homeeconomics_user
--

ALTER TABLE ONLY public.families
    ADD CONSTRAINT families_name_key UNIQUE (name);


--
-- Name: families families_pkey; Type: CONSTRAINT; Schema: public; Owner: homeeconomics_user
--

ALTER TABLE ONLY public.families
    ADD CONSTRAINT families_pkey PRIMARY KEY (id);


--
-- Name: transactions transactions_pkey; Type: CONSTRAINT; Schema: public; Owner: homeeconomics_user
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: homeeconomics_user
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: ix_families_id; Type: INDEX; Schema: public; Owner: homeeconomics_user
--

CREATE INDEX ix_families_id ON public.families USING btree (id);


--
-- Name: ix_transactions_family_id; Type: INDEX; Schema: public; Owner: homeeconomics_user
--

CREATE INDEX ix_transactions_family_id ON public.transactions USING btree (family_id);


--
-- Name: ix_transactions_id; Type: INDEX; Schema: public; Owner: homeeconomics_user
--

CREATE INDEX ix_transactions_id ON public.transactions USING btree (id);


--
-- Name: ix_transactions_user_id; Type: INDEX; Schema: public; Owner: homeeconomics_user
--

CREATE INDEX ix_transactions_user_id ON public.transactions USING btree (user_id);


--
-- Name: ix_transactions_user_phone; Type: INDEX; Schema: public; Owner: homeeconomics_user
--

CREATE INDEX ix_transactions_user_phone ON public.transactions USING btree (user_phone);


--
-- Name: ix_users_id; Type: INDEX; Schema: public; Owner: homeeconomics_user
--

CREATE INDEX ix_users_id ON public.users USING btree (id);


--
-- Name: ix_users_phone; Type: INDEX; Schema: public; Owner: homeeconomics_user
--

CREATE UNIQUE INDEX ix_users_phone ON public.users USING btree (phone);


--
-- Name: transactions transactions_family_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: homeeconomics_user
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_family_id_fkey FOREIGN KEY (family_id) REFERENCES public.families(id);


--
-- Name: transactions transactions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: homeeconomics_user
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: users users_family_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: homeeconomics_user
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_family_id_fkey FOREIGN KEY (family_id) REFERENCES public.families(id);


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: -; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres GRANT ALL ON SEQUENCES TO homeeconomics_user;


--
-- Name: DEFAULT PRIVILEGES FOR TYPES; Type: DEFAULT ACL; Schema: -; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres GRANT ALL ON TYPES TO homeeconomics_user;


--
-- Name: DEFAULT PRIVILEGES FOR FUNCTIONS; Type: DEFAULT ACL; Schema: -; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres GRANT ALL ON FUNCTIONS TO homeeconomics_user;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: -; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres GRANT ALL ON TABLES TO homeeconomics_user;


--
-- PostgreSQL database dump complete
--

\unrestrict iC5LUrLtzun0tJlkcJWNEZSgg40UEZgroGaCwVVWcJ0gBdvNJUAXHSnVXeBmnoq

