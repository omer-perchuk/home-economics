"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import WhatsAppGuideDemo from "@/components/WhatsAppGuideDemo";
import {
  BookOpen,
  ChartPie,
  FileBarChart2,
  Globe,
  HelpCircle,
  Home,
  Menu,
  MessageCircleMore,
  PencilLine,
  Plus,
  Rows3,
  Sparkles,
  SquarePen,
  Trash2,
} from "lucide-react";

type GuideSectionProps = {
  badge: string;
  title: string;
  subtitle: string;
  accentClass: string;
  children: React.ReactNode;
  immediate?: boolean;
};

function useReveal<T extends HTMLElement>() {
  const ref = useRef<T | null>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          observer.disconnect();
        }
      },
      {
        threshold: 0.2,
        rootMargin: "0px 0px -40px 0px",
      }
    );

    observer.observe(node);

    return () => observer.disconnect();
  }, []);

  return { ref, visible };
}

function GuideSection({
  badge,
  title,
  subtitle,
  accentClass,
  children,
  immediate = false,
}: GuideSectionProps) {
  const { ref, visible: revealed } = useReveal<HTMLElement>();
  const visible = immediate || revealed;

  return (
    <section
      ref={ref}
      className={`min-h-[31rem] rounded-[2.25rem] border border-white/80 bg-white/88 p-5 text-center shadow-[0_18px_45px_rgba(16,185,129,0.10)] backdrop-blur transition-all duration-700 md:min-h-[34rem] md:p-7 ${
        visible
          ? "translate-y-0 opacity-100"
          : "translate-y-8 opacity-0"
      }`}
    >
      <div
        className={`mx-auto inline-flex items-center rounded-full bg-gradient-to-r px-4 py-1.5 text-xs font-semibold tracking-[0.24em] text-slate-700 shadow-sm ${accentClass}`}
      >
        {badge}
      </div>

      <h2 className="mx-auto mt-5 max-w-[14ch] text-[2.5rem] font-black leading-[0.98] text-slate-950 md:text-[3rem]">
        {title}
      </h2>

      <p className="mx-auto mt-3 max-w-[28ch] text-sm leading-7 text-slate-600 md:text-base">
        {subtitle}
      </p>

      <div className="mt-6 flex h-[calc(100%-11rem)] flex-col justify-center">
        {children}
      </div>
    </section>
  );
}

function FeatureBubble({
  icon,
  title,
  text,
}: {
  icon: React.ReactNode;
  title: string;
  text: string;
}) {
  return (
    <div className="rounded-[1.8rem] border border-white/80 bg-gradient-to-br from-white to-emerald-50 p-4 shadow-[0_10px_24px_rgba(15,23,42,0.05)] transition duration-300 hover:-translate-y-1 hover:shadow-[0_16px_32px_rgba(16,185,129,0.12)]">
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-900 text-emerald-300 shadow-sm">
        {icon}
      </div>
      <div className="mt-3 text-base font-bold text-slate-900">{title}</div>
      <p className="mt-2 text-sm leading-6 text-slate-600">{text}</p>
    </div>
  );
}

export default function GuidePage() {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <main
      dir="rtl"
      className="relative min-h-screen overflow-hidden bg-gradient-to-b from-green-50 via-emerald-50 to-lime-50 text-slate-900"
    >
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="animate-pulse-soft absolute right-[-3rem] top-24 h-44 w-44 rounded-full bg-emerald-300/30 blur-3xl" />
        <div className="animate-float-soft absolute left-[-2rem] top-[26rem] h-40 w-40 rounded-full bg-lime-300/25 blur-3xl" />
        <div className="animate-pulse-soft absolute bottom-20 right-10 h-56 w-56 rounded-full bg-green-200/30 blur-3xl" />
      </div>

      {menuOpen && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/30"
            onClick={() => setMenuOpen(false)}
          />

          <div className="fixed right-0 top-0 z-50 h-full w-64 space-y-6 bg-white p-5 text-center shadow-xl">
            <div className="text-xl font-bold text-green-600">תפריט</div>

            <Link
              href="/"
              onClick={() => setMenuOpen(false)}
              className="flex items-center justify-center gap-2 text-lg"
            >
              <Home size={20} />
              דף הבית
            </Link>

            <Link
              href="/reports"
              onClick={() => setMenuOpen(false)}
              className="flex items-center justify-center gap-2 text-lg"
            >
              <FileBarChart2 size={20} />
              דוחות
            </Link>

            <Link
              href="/guide"
              onClick={() => setMenuOpen(false)}
              className="flex items-center justify-center gap-2 text-lg"
            >
              <BookOpen size={20} />
              מדריך
            </Link>
          </div>
        </>
      )}

      <div className="relative mx-auto max-w-md px-4 pb-10 pt-4 md:max-w-3xl">
        <header className="mb-4 flex items-center justify-between">
          <button
            onClick={() => setMenuOpen(true)}
            className="rounded-full bg-white/80 p-2 shadow-sm transition hover:scale-[1.04] hover:bg-white"
            aria-label="פתיחת תפריט"
          >
            <Menu />
          </button>

          <div className="rounded-full border border-white/80 bg-white/85 px-4 py-2 text-center shadow-sm backdrop-blur">
            <div className="flex items-center justify-center gap-2">
              <div className="bg-[linear-gradient(135deg,#047857_0%,#0f172a_48%,#16a34a_100%)] bg-clip-text text-lg font-black text-transparent md:text-xl">
                CashBot - המדריך
              </div>
            </div>
          </div>

          <div className="w-10" />
        </header>

        <div className="space-y-5">
          <GuideSection
            badge="WELCOME"
            title="ברוכים הבאים לעוזר הפיננסי שלך"
            subtitle="המערכת עוזרת לנהל הוצאות והכנסות למשפחה, עם סיווג אוטומטי ותצוגה ברורה של כל הנתונים."
            accentClass="from-emerald-100 via-lime-100 to-white"
          >
            <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
              <FeatureBubble
                icon={<MessageCircleMore size={20} />}
                title="שולחים הודעה"
                text="מעדכנים הוצאה או הכנסה ישירות ב-WhatsApp."
              />
              <FeatureBubble
                icon={<Sparkles size={20} />}
                title="המערכת מסווגת"
                text="הרשומה נשמרת עם קטגוריה וסוג לפי היכולות הקיימות."
              />
              <FeatureBubble
                icon={<ChartPie size={20} />}
                title="רואים תמונה ברורה"
                text="באתר רואים סכומים, גרפים ופילוח לפי קטגוריות."
              />
            </div>
          </GuideSection>

          <GuideSection
            badge="WHATSAPP BOT"
            title="איך משתמשים בבוט בוואטסאפ"
            subtitle="כל הפעולות החשובות זמינות דרך הודעות קצרות ופשוטות."
            accentClass="from-green-100 via-emerald-100 to-white"
            immediate
          >
            <div className="flex flex-col items-center gap-4">
              <div className="grid w-full grid-cols-1 gap-3 md:grid-cols-2">
                <FeatureBubble
                  icon={<Plus size={20} />}
                  title="הוספת רשומה"
                  text="שולחים תיאור וסכום. למשל: ארומה 32 או משכורת 12000."
                />
                <FeatureBubble
                  icon={<Sparkles size={20} />}
                  title="סיווג אוטומטי"
                  text="הבוט שומר את הרשומה עם קטגוריה וסוג לפי מה שהוא מזהה."
                />
                <FeatureBubble
                  icon={<Rows3 size={20} />}
                  title="סיכום"
                  text="שולחים סיכום כדי לראות תמונה חודשית. אפשר גם: סיכום 3/2025."
                />
                <FeatureBubble
                  icon={<SquarePen size={20} />}
                  title="עדכון ומחיקה"
                  text="שולחים עדכן או מחק, בוחרים מספר רשומה, וממשיכים לפי ההנחיות."
                />
              </div>

              <div className="rounded-[2rem] border border-white/80 bg-gradient-to-br from-white/85 via-emerald-50/80 to-lime-50/70 p-4 shadow-[0_14px_30px_rgba(16,185,129,0.10)]">
                <WhatsAppGuideDemo />
              </div>
            </div>
          </GuideSection>

          <GuideSection
            badge="WEBSITE"
            title="מה אפשר לעשות באתר"
            subtitle="ממשק נקי לניהול שוטף של הנתונים והדוחות."
            accentClass="from-lime-100 via-emerald-100 to-white"
            immediate
          >
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              <FeatureBubble
                icon={<Globe size={20} />}
                title="צפייה בחודש הנוכחי"
                text="רואים את הנתונים של החודש הנבחר בצורה ברורה."
              />
              <FeatureBubble
                icon={<ChartPie size={20} />}
                title="גרפים ופילוח"
                text="רואים תרשימים והתפלגות לפי קטגוריות."
              />
              <FeatureBubble
                icon={<Rows3 size={20} />}
                title="סינון לפי קטגוריה"
                text="אפשר לבחור קטגוריה ולראות רק את הרשומות הרלוונטיות."
              />
              <FeatureBubble
                icon={<PencilLine size={20} />}
                title="הוספה, עריכה ומחיקה"
                text="אפשר להוסיף רשומות חדשות, לערוך קיימות ולמחוק לפי הצורך."
              />
            </div>
          </GuideSection>
        </div>

        <div className="mt-6 text-center">
          <div className="mx-auto inline-flex items-center gap-2 rounded-full bg-slate-900 px-4 py-2 text-sm font-medium text-white shadow-[0_14px_34px_rgba(15,23,42,0.18)]">
            <HelpCircle size={16} />
            טיפ: בוואטסאפ אפשר לשלוח גם עזרה כדי לפתוח את המדריך
          </div>
        </div>
      </div>
    </main>
  );
}
