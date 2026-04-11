import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { MessageCircle, CheckCircle2, Bot, Globe, BarChart3, Trash2, Pencil, ChevronDown } from "lucide-react";

type ChatItem = {
  id: string;
  side: "user" | "bot";
  text: string;
  icon?: React.ReactNode;
  ctaLabel?: string;
  typing?: boolean;
};

type Step =
  | { kind: "message"; side: "user" | "bot"; text: string; delay?: number; icon?: React.ReactNode; ctaLabel?: string }
  | { kind: "typing"; delay?: number }
  | { kind: "pause"; delay?: number };

const STEPS: Step[] = [
  { kind: "message", side: "user", text: "ארומה 18", delay: 700 },
  { kind: "typing", delay: 900 },
  { kind: "message", side: "bot", text: "✅ נוסף 18 ₪ לקטגוריה: ☕ אוכל בחוץ וקפה", icon: <CheckCircle2 className="h-4 w-4" />, delay: 700 },

  { kind: "message", side: "user", text: "תוסיף 500 שח בסופר", delay: 900 },
  { kind: "typing", delay: 900 },
  { kind: "message", side: "bot", text: "✅ נוסף 500 ₪ לקטגוריה: 🛒 סופר וקניות לבית", icon: <CheckCircle2 className="h-4 w-4" />, delay: 700 },

  { kind: "message", side: "user", text: "קניתי מקדונלדס 100", delay: 900 },
  { kind: "typing", delay: 900 },
  { kind: "message", side: "bot", text: "✅ נוסף 100 ₪ לקטגוריה: ☕ אוכל בחוץ וקפה", icon: <CheckCircle2 className="h-4 w-4" />, delay: 700 },

  { kind: "message", side: "user", text: "עדכן", delay: 1000 },
  { kind: "typing", delay: 850 },
  { kind: "message", side: "bot", text: "📋 רשומות החודש\n\n1. ☕ ארומה — 18 ₪\n2. 🛒 סופר — 500 ₪\n3. ☕ מקדונלדס — 100 ₪\n\n✏️ שלח את מספר הרשומה לעדכון", icon: <Pencil className="h-4 w-4" />, delay: 900 },
  { kind: "message", side: "user", text: "3", delay: 900 },
  { kind: "typing", delay: 850 },
  { kind: "message", side: "bot", text: "✏️ שלח ערך חדש.\nלדוגמה: ארומה 42", icon: <Pencil className="h-4 w-4" />, delay: 700 },
  { kind: "message", side: "user", text: "מקדונלדס 120", delay: 900 },
  { kind: "typing", delay: 850 },
  { kind: "message", side: "bot", text: "✏️ עודכן: 120 ₪ · ☕ אוכל בחוץ וקפה", icon: <Pencil className="h-4 w-4" />, delay: 800 },

  { kind: "message", side: "user", text: "תוסיף רשומה של ארומה 18", delay: 1000 },
  { kind: "typing", delay: 850 },
  { kind: "message", side: "bot", text: "✅ נוסף 18 ₪ לקטגוריה: ☕ אוכל בחוץ וקפה", icon: <CheckCircle2 className="h-4 w-4" />, delay: 800 },
  { kind: "message", side: "user", text: "אופס הוספתי את זה כבר", delay: 1000 },
  { kind: "message", side: "user", text: "מחק", delay: 600 },
  { kind: "typing", delay: 850 },
  { kind: "message", side: "bot", text: "📋 רשומות החודש\n\n1. ☕ ארומה — 18 ₪\n2. 🛒 סופר — 500 ₪\n3. ☕ מקדונלדס — 120 ₪\n4. ☕ ארומה — 18 ₪\n\n🗑️ שלח מספר רשומה או כמה מספרים למחיקה", icon: <Trash2 className="h-4 w-4" />, delay: 850 },
  { kind: "message", side: "user", text: "4", delay: 800 },
  { kind: "typing", delay: 800 },
  { kind: "message", side: "bot", text: "🗑️ נמחקו 1 רשומות:\n\nארומה — 18 ₪", icon: <Trash2 className="h-4 w-4" />, delay: 850 },

  { kind: "message", side: "user", text: "הצג", delay: 1000 },
  { kind: "typing", delay: 850 },
  { kind: "message", side: "bot", text: "📋 רשומות החודש\n\n1. ☕ ארומה — 18 ₪\n2. 🛒 סופר — 500 ₪\n3. ☕ מקדונלדס — 120 ₪", icon: <MessageCircle className="h-4 w-4" />, ctaLabel: "לחץ להיכנס לאתר 👇", delay: 1000 },

  { kind: "message", side: "user", text: "סיכום", delay: 1000 },
  { kind: "typing", delay: 800 },
  { kind: "message", side: "bot", text: "📊 סיכום 4/2026\n\n☕ אוכל בחוץ וקפה: 138 ₪\n🛒 סופר וקניות לבית: 500 ₪\n\nסה״כ: 638 ₪\n\n💡 לחודש אחר שלח: סיכום 3/2025", icon: <BarChart3 className="h-4 w-4" />, ctaLabel: "לחץ להיכנס לאתר 👇", delay: 1000 },

  { kind: "message", side: "user", text: "אתר", delay: 1000 },
  { kind: "typing", delay: 800 },
  { kind: "message", side: "bot", text: "🔐 כניסה מאובטחת לאתר", icon: <Globe className="h-4 w-4" />, ctaLabel: "לחץ להיכנס לאתר 👇", delay: 900 },

  { kind: "message", side: "user", text: "עזרה", delay: 1000 },
  { kind: "typing", delay: 800 },
  { kind: "message", side: "bot", text: "💡 איך משתמשים בבוט?\n\n📝 הוספת רשומה\n📋 הצג / רשומות\n📊 סיכום\n🌐 אתר\n✏️ עדכן\n🗑️ מחק", icon: <Globe className="h-4 w-4" />, ctaLabel: "פתח את מדריך ההתחלה 👇", delay: 1000 },
];

function BotTyping() {
  return (
    <div className="flex justify-end">
      <div className="rounded-3xl bg-white px-4 py-3 shadow-sm ring-1 ring-slate-200">
        <div className="flex items-center gap-1">
          <span className="h-2 w-2 animate-bounce rounded-full bg-slate-400 [animation-delay:-0.2s]" />
          <span className="h-2 w-2 animate-bounce rounded-full bg-slate-400 [animation-delay:-0.1s]" />
          <span className="h-2 w-2 animate-bounce rounded-full bg-slate-400" />
        </div>
      </div>
    </div>
  );
}

function Bubble({ side, text, icon, ctaLabel }: { side: "user" | "bot"; text: string; icon?: React.ReactNode; ctaLabel?: string }) {
  const isUser = side === "user";
  return (
    <div className={`flex ${isUser ? "justify-start" : "justify-end"}`}>
      <motion.div
        initial={{ opacity: 0, y: 12, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.28 }}
        className={`max-w-[86%] rounded-[26px] px-4 py-3 text-sm leading-6 shadow-sm ${
          isUser
            ? "bg-emerald-600 text-white"
            : "bg-white text-slate-800 ring-1 ring-slate-200"
        }`}
      >
        {!isUser && icon ? <div className="mb-1 flex items-center justify-end gap-1 text-emerald-700">{icon}<span className="text-xs font-semibold">הבוט</span></div> : null}
        <div className="whitespace-pre-line text-right">{text}</div>
        {!isUser && ctaLabel ? (
          <div className="mt-3 flex justify-end">
            <button
              type="button"
              className="rounded-full bg-emerald-600 px-3 py-2 text-xs font-semibold text-white shadow-sm transition hover:bg-emerald-700"
            >
              {ctaLabel}
            </button>
          </div>
        ) : null}
      </motion.div>
    </div>
  );
}

export default function WhatsAppGuideDemo() {
  const [messages, setMessages] = useState<ChatItem[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const scrollRef = React.useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function run() {
      while (!cancelled) {
        setMessages([]);
        setIsTyping(false);
        if (scrollRef.current) {
          scrollRef.current.scrollTo({ top: 0, behavior: "auto" });
        }

        await new Promise((r) => setTimeout(r, 1200));
        if (cancelled) return;

        for (let i = 0; i < STEPS.length; i += 1) {
          const step = STEPS[i];
          const delay = step.delay ?? 800;
          await new Promise((r) => setTimeout(r, delay));
          if (cancelled) return;

          if (step.kind === "typing") {
            setIsTyping(true);
            continue;
          }

          if (step.kind === "pause") {
            continue;
          }

          setIsTyping(false);
          setMessages((prev) => [
            ...prev,
            {
              id: `${i}-${Date.now()}`,
              side: step.side,
              text: step.text,
              icon: step.icon,
              ctaLabel: step.ctaLabel,
            },
          ]);
        }

        setIsTyping(false);
        await new Promise((r) => setTimeout(r, 60000));
        if (cancelled) return;
      }
    }

    run();
    return () => {
      cancelled = true;
    };
  }, []);

  function scrollChatBy(amount: number) {
    const container = scrollRef.current;
    if (!container) return;

    container.scrollBy({
      top: amount,
      behavior: "smooth",
    });
  }

  return (
    <div className="mx-auto w-full max-w-[19rem]">
      <div className="rounded-[2.8rem] bg-[linear-gradient(180deg,#111827_0%,#0f172a_100%)] p-[10px] shadow-[0_28px_70px_rgba(15,23,42,0.28)] ring-1 ring-slate-900/10">
        <div className="rounded-[2.35rem] bg-[#efeae2]">
          <div className="flex justify-center pt-3">
            <div className="h-1.5 w-24 rounded-full bg-slate-900/80" />
          </div>

          <div className="mt-2 flex items-center justify-between rounded-t-[2rem] bg-[#075e54] px-4 py-3 text-white">
            <div className="text-right">
              <div className="text-sm font-bold">Home Economics Bot</div>
              <div className="text-[11px] text-white/80">online</div>
            </div>
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-emerald-400/30">
              <Bot className="h-5 w-5" />
            </div>
          </div>

          <div
            ref={scrollRef}
            className="h-[540px] overflow-y-auto bg-[linear-gradient(rgba(255,255,255,0.68),rgba(255,255,255,0.68)),url('https://images.unsplash.com/photo-1512428559087-560fa5ceab42?q=80&w=1200&auto=format&fit=crop')] bg-cover bg-center p-3 [scrollbar-width:none] [-ms-overflow-style:none]"
          >
            <style jsx>{`
              div::-webkit-scrollbar {
                display: none;
              }
            `}</style>
            <AnimatePresence>
              <div className="space-y-3">
                {messages.map((msg) => (
                  <Bubble key={msg.id} side={msg.side} text={msg.text} icon={msg.icon} ctaLabel={msg.ctaLabel} />
                ))}
                {isTyping ? <BotTyping /> : null}
                {messages.length === 0 ? (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="flex h-[360px] items-center justify-center"
                  >
                    <div className="rounded-[1.6rem] bg-white/75 px-4 py-3 text-center text-sm text-slate-500 ring-1 ring-white/70 backdrop-blur">
                      שיחת וואטסאפ חדשה
                    </div>
                  </motion.div>
                ) : null}
                <div className="h-56" />
              </div>
            </AnimatePresence>
          </div>

          <div className="rounded-b-[2.35rem] bg-[#f0f2f5] px-4 py-3">
            <div className="flex items-center justify-between gap-3">
              <button
                type="button"
                onClick={() => scrollChatBy(220)}
                className="flex items-center gap-1 rounded-full bg-emerald-600 px-3 py-2 text-xs font-semibold text-white shadow-sm transition hover:bg-emerald-700"
              >
                <ChevronDown className="h-4 w-4" />
                גלול בשיחה
              </button>
              <div className="text-center text-xs text-slate-500">
                {messages.length === 0 ? "שיחה חדשה" : "אפשר לגלול כדי לראות דוגמאות"}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
