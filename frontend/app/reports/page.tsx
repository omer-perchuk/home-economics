"use client";

import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import { Home, Menu, FileBarChart2 } from "lucide-react";

type MonthOption = {
  year: number;
  month: number;
};

type SummaryCategory = {
  category: string;
  amount: number;
};

type Summary = {
  month: number;
  year: number;
  expenses_total: number;
  income_total: number;
  balance: number;
  categories: SummaryCategory[];
};

type ChartRow = {
  monthLabel: string;
  [key: string]: string | number;
};

const monthNames: Record<number, string> = {
  1: "ינו",
  2: "פבר",
  3: "מרץ",
  4: "אפר",
  5: "מאי",
  6: "יונ",
  7: "יול",
  8: "אוג",
  9: "ספט",
  10: "אוק",
  11: "נוב",
  12: "דצמ",
};

const categoryColors: Record<string, string> = {
  "סופר וקניות לבית": "#3b82f6",
  "אוכל בחוץ וקפה": "#f59e0b",
  "תחבורה": "#10b981",
  "בריאות ופארם": "#ef4444",
  "דיור וחשבונות": "#8b5cf6",
  "בילויים ופנאי": "#ec4899",
  "הכנסות": "#22c55e",
  "אחר": "#94a3b8",
};

const searchParams = useSearchParams();
const FAMILY_NAME = searchParams.get("family") || "משפחת עומר";

function formatCurrency(value: number) {
  return `₪${value.toLocaleString("he-IL", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  })}`;
}

export default function ReportsPage() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [months, setMonths] = useState<MonthOption[]>([]);
  const [selectedYear, setSelectedYear] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [chartData, setChartData] = useState<ChartRow[]>([]);
  const [allCategories, setAllCategories] = useState<string[]>([]);

  const backendUrl =
    process.env.NEXT_PUBLIC_API_URL || "https://home-economics.onrender.com";

useEffect(() => {
  loadMonths();
}, [FAMILY_NAME]);

  useEffect(() => {
    if (selectedYear) {
      loadYearData(selectedYear);
    }
  }, [selectedYear, months]);

  async function loadMonths() {
    try {
      setError("");

      const res = await fetch(
        `${backendUrl}/api/months?family_name=${encodeURIComponent(FAMILY_NAME)}`
      );
      const data: MonthOption[] = await res.json();

      setMonths(data);

      if (data.length > 0) {
        const years = [...new Set(data.map((m) => m.year))].sort((a, b) => b - a);
        setSelectedYear(years[0]);
      } else {
        setSelectedYear(new Date().getFullYear());
      }
    } catch (err) {
      setError(String(err));
      setLoading(false);
    }
  }

  async function loadYearData(year: number) {
    try {
      setLoading(true);
      setError("");

      const yearMonths = months
        .filter((m) => m.year === year)
        .sort((a, b) => a.month - b.month);

      if (yearMonths.length === 0) {
        setChartData([]);
        setAllCategories([]);
        setLoading(false);
        return;
      }

      const summaries: Summary[] = await Promise.all(
        yearMonths.map(async (m) => {
          const res = await fetch(
            `${backendUrl}/api/summary?month=${m.month}&year=${m.year}&family_name=${encodeURIComponent(FAMILY_NAME)}`
          );
          return res.json();
        })
      );

      const categoriesSet = new Set<string>();
      summaries.forEach((summary) => {
        summary.categories.forEach((cat) => categoriesSet.add(cat.category));
      });

      const categories = Array.from(categoriesSet);
      setAllCategories(categories);

      const rows: ChartRow[] = summaries.map((summary) => {
        const row: ChartRow = {
          monthLabel: monthNames[summary.month] || String(summary.month),
        };

        categories.forEach((catName) => {
          row[catName] = 0;
        });

        summary.categories.forEach((cat) => {
          row[cat.category] = cat.amount;
        });

        return row;
      });

      setChartData(rows);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  const availableYears = useMemo(() => {
    const years = [...new Set(months.map((m) => m.year))].sort((a, b) => b - a);
    return years;
  }, [months]);

  return (
    <main className="relative min-h-screen overflow-hidden bg-gradient-to-b from-green-50 via-emerald-50 to-lime-50 text-slate-900">
      {menuOpen && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/30"
            onClick={() => setMenuOpen(false)}
          />
          <div className="fixed right-0 top-0 z-50 h-full w-64 space-y-6 bg-white p-5 shadow-xl">
            <div className="text-xl font-bold text-green-600">תפריט</div>

            <Link
              href="/"
              onClick={() => setMenuOpen(false)}
              className="flex items-center gap-2 text-lg"
            >
              <Home size={20} />
              דף הבית
            </Link>

            <Link
              href="/reports"
              onClick={() => setMenuOpen(false)}
              className="flex items-center gap-2 text-lg"
            >
              <FileBarChart2 size={20} />
              דוחות
            </Link>
          </div>
        </>
      )}

      <div className="relative mx-auto max-w-md space-y-6 p-4">
        <div className="sticky top-0 z-30 flex items-center justify-between rounded-[2rem] border border-green-100 bg-white/95 px-6 py-6 shadow-[0_0_0_1px_rgba(34,197,94,0.05),0_8px_24px_rgba(16,185,129,0.08)] backdrop-blur">
          <button onClick={() => setMenuOpen(true)} className="p-2 text-slate-900">
            <Menu size={30} />
          </button>

          <h1 className="flex items-center gap-2 text-3xl font-bold text-green-700">
            <span>💸</span>
            <span>דוחות</span>
          </h1>

          <div className="w-10" />
        </div>

        {error && (
          <div className="rounded-2xl bg-red-50 p-4 text-sm text-red-700 shadow-sm">
            {error}
          </div>
        )}

        <div className="rounded-[2rem] border border-green-100 bg-white p-6 shadow-[0_8px_24px_rgba(16,185,129,0.08)]">
          <label className="mb-4 block text-2xl font-medium text-slate-800">
            בחירת שנה
          </label>

          <select
            className="w-full rounded-[1.2rem] border-2 border-slate-800 bg-white p-4 text-xl"
            value={selectedYear ?? ""}
            onChange={(e) => setSelectedYear(Number(e.target.value))}
          >
            {availableYears.map((year) => (
              <option key={year} value={year}>
                {year}
              </option>
            ))}
          </select>
        </div>

        <div className="rounded-[2rem] border border-green-100 bg-white p-6 shadow-[0_8px_24px_rgba(16,185,129,0.08)]">
          <div className="mb-6 text-3xl font-bold text-slate-900">
            הוצאות לפי חודשים בשנת {selectedYear}
          </div>

          <div className="h-[520px] w-full">
            {loading ? (
              <div className="flex h-full items-center justify-center text-slate-500">
                טוען נתונים...
              </div>
            ) : chartData.length === 0 ? (
              <div className="flex h-full items-center justify-center text-slate-500">
                אין נתונים לשנה הזו
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="4 4" />
                  <XAxis dataKey="monthLabel" />
                  <YAxis />
                  <Tooltip formatter={(value) => formatCurrency(Number(value))} />
                  {allCategories.map((category) => (
                    <Bar
                      key={category}
                      dataKey={category}
                      stackId="a"
                      fill={categoryColors[category] || "#94a3b8"}
                      radius={[4, 4, 0, 0]}
                    />
                  ))}
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        <div className="rounded-[2rem] border border-green-100 bg-white p-6 shadow-[0_8px_24px_rgba(16,185,129,0.08)]">
          <div className="mb-4 text-3xl font-bold text-slate-900">מקרא קטגוריות</div>

          <div className="space-y-3">
            {allCategories.length === 0 ? (
              <div className="text-slate-500">אין קטגוריות להצגה</div>
            ) : (
              allCategories.map((category) => (
                <div key={category} className="flex items-center gap-3">
                  <span
                    className="h-4 w-4 rounded-full"
                    style={{ backgroundColor: categoryColors[category] || "#94a3b8" }}
                  />
                  <span className="text-lg text-slate-800">{category}</span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </main>
  );
}