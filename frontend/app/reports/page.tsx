"use client";

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
  Legend,
} from "recharts";
import { Home, Menu, X, FileBarChart2 } from "lucide-react";

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

const monthNames: Record<number, string> = {
  1: "ינואר",
  2: "פברואר",
  3: "מרץ",
  4: "אפריל",
  5: "מאי",
  6: "יוני",
  7: "יולי",
  8: "אוגוסט",
  9: "ספטמבר",
  10: "אוקטובר",
  11: "נובמבר",
  12: "דצמבר",
};

const categoryColors: Record<string, string> = {
  "סופר וקניות לבית": "#3b82f6",
  "אוכל בחוץ וקפה": "#f59e0b",
  "תחבורה": "#10b981",
  "בריאות ופארם": "#ef4444",
  "דיור וחשבונות": "#8b5cf6",
  "בילויים ופנאי": "#ec4899",
  "אחר": "#94a3b8",
};

function formatCurrency(value: number) {
  return `₪${value.toLocaleString("he-IL", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  })}`;
}

export default function ReportsPage() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [months, setMonths] = useState<MonthOption[]>([]);
  const [summaries, setSummaries] = useState<Summary[]>([]);
  const [selectedYear, setSelectedYear] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  const backendUrl = "http://192.168.68.101:8000";

  useEffect(() => {
    async function loadReports() {
      setLoading(true);

      const monthsRes = await fetch(`${backendUrl}/api/months`);
      const monthsData: MonthOption[] = await monthsRes.json();
      setMonths(monthsData);

      const summaryPromises = monthsData.map(async (m) => {
        const res = await fetch(
          `${backendUrl}/api/summary?month=${m.month}&year=${m.year}`
        );
        return res.json();
      });

      const allSummaries: Summary[] = await Promise.all(summaryPromises);
      setSummaries(allSummaries);

      const years = [...new Set(monthsData.map((m) => m.year))].sort((a, b) => b - a);
      if (years.length > 0) {
        setSelectedYear(years[0]);
      }

      setLoading(false);
    }

    loadReports();
  }, []);

  const availableYears = useMemo(() => {
    return [...new Set(months.map((m) => m.year))].sort((a, b) => b - a);
  }, [months]);

  const allCategories = useMemo(() => {
    const categorySet = new Set<string>();

    summaries.forEach((summary) => {
      summary.categories.forEach((cat) => {
        if (cat.category !== "הכנסות") {
          categorySet.add(cat.category);
        }
      });
    });

    return Array.from(categorySet);
  }, [summaries]);

  const chartData = useMemo(() => {
    if (!selectedYear) return [];

    return Array.from({ length: 12 }, (_, index) => {
      const month = index + 1;
      const matchingSummary = summaries.find(
        (s) => s.year === selectedYear && s.month === month
      );

      const row: Record<string, string | number> = {
        monthLabel: monthNames[month],
      };

      allCategories.forEach((category) => {
        row[category] =
          matchingSummary?.categories.find((c) => c.category === category)?.amount || 0;
      });

      return row;
    });
  }, [selectedYear, summaries, allCategories]);

  return (
    <main className="min-h-screen bg-gradient-to-b from-green-50 via-emerald-50 to-lime-50 p-4 text-slate-900">
      {menuOpen && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/30"
            onClick={() => setMenuOpen(false)}
          />
          <div className="fixed right-0 top-0 z-50 h-full w-64 space-y-6 bg-white p-5 shadow-xl">
            <div className="flex items-center justify-between">
              <div className="text-xl font-bold text-green-600">תפריט</div>
              <button onClick={() => setMenuOpen(false)}>
                <X size={22} />
              </button>
            </div>

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

      <div className="mx-auto max-w-md space-y-4">
        <div className="rounded-3xl border border-green-100 bg-white/90 p-4 shadow">
          <div className="flex items-center justify-between">
            <button onClick={() => setMenuOpen(true)} className="p-2">
              <Menu size={26} />
            </button>

            <div className="flex items-center gap-2 text-green-700">
              <span className="text-xl">💸</span>
              <h1 className="text-2xl font-bold">דוחות</h1>
            </div>

            <div className="w-10" />
          </div>
        </div>

        <div className="rounded-3xl border border-green-100 bg-white/90 p-4 shadow">
          <div className="mb-2 text-sm font-medium text-slate-700">בחירת שנה</div>

          <select
            className="w-full rounded-xl border p-3"
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

        <div className="rounded-3xl border border-green-100 bg-white/90 p-4 shadow">
          <div className="mb-4 text-lg font-semibold">
            הוצאות לפי חודשים בשנת {selectedYear ?? ""}
          </div>

          {loading ? (
            <div className="text-sm text-slate-500">טוען דוחות...</div>
          ) : (
            <div className="h-[420px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="monthLabel" />
                  <YAxis />
                  <Tooltip formatter={(value) => formatCurrency(Number(value))} />
                  {allCategories.map((category) => (
                    <Bar
                      key={category}
                      dataKey={category}
                      stackId="expenses"
                      fill={categoryColors[category] || "#94a3b8"}
                      radius={[2, 2, 0, 0]}
                    />
                  ))}
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        <div className="rounded-3xl border border-green-100 bg-white/90 p-4 shadow">
          <div className="mb-3 text-lg font-semibold">מקרא קטגוריות</div>

          <div className="space-y-2">
            {allCategories.map((category) => (
              <div
                key={category}
                className="flex items-center justify-between rounded-2xl bg-slate-50 px-3 py-3"
              >
                <div className="flex items-center gap-2">
                  <span
                    className="h-3 w-3 rounded-full"
                    style={{
                      backgroundColor: categoryColors[category] || "#94a3b8",
                    }}
                  />
                  <span>{category}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </main>
  );
}