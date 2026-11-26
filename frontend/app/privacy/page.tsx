export const metadata = {
  title: "מדיניות פרטיות | כלכלת הבית",
};

export default function PrivacyPage() {
  return (
    <main
      dir="rtl"
      className="mx-auto max-w-2xl space-y-4 p-6 text-slate-800 leading-relaxed"
    >
      <h1 className="text-2xl font-bold text-green-700">מדיניות פרטיות</h1>

      <p>
        &quot;כלכלת הבית&quot; הוא כלי משפחתי לניהול הוצאות והכנסות. הדף הזה מסביר
        איזה מידע נשמר ולמה.
      </p>

      <h2 className="text-lg font-semibold">מה נשמר</h2>
      <ul className="list-disc space-y-1 pr-6">
        <li>שם ומספר טלפון, לצורך זיהוי בבוט בוואטסאפ.</li>
        <li>ההוצאות וההכנסות שהמשפחה מזינה.</li>
        <li>
          אם בחרת לחבר חשבון Google: המזהה של החשבון וכתובת המייל שלו, רק כדי
          לאפשר כניסה לאתר. לא נקראים אנשי קשר, קבצים או מיילים.
        </li>
      </ul>

      <h2 className="text-lg font-semibold">שימוש במידע</h2>
      <p>
        המידע משמש רק להצגת הנתונים לבני המשפחה עצמם. הוא לא נמכר ולא מועבר
        לגורם שלישי, מלבד שירותי התשתית שמפעילים את האתר והבוט.
      </p>

      <h2 className="text-lg font-semibold">מחיקה וניתוק</h2>
      <p>
        אפשר לנתק את חשבון Google בכל רגע מהתפריט באתר. לבקשת מחיקה של כל
        המידע אפשר לפנות למנהל המשפחה או לשלוח הודעה לבוט.
      </p>
    </main>
  );
}
