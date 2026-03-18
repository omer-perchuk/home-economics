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
  Cell,
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
  תחבורה: "#10b981",
  "בריאות ופארם": "#ef4444",
  "דיור וחשבונות": "#8b5cf6",
  "בילויים ופנאי": "#ec4899",
  אחר: "#94a3b8",
};

function formatCurrency(value: number) {
  return `₪${value.toLocaleString("he-IL", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  })}`;
}

export default function ReportsPage() {
  const FAMILY_ID =
    typeof window !== "undefined"
      ? Number(new URLSearchParams(window.location.search).get("family_id") || "1")
      : 1;
  const backendUrl =
    process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const [menuOpen, setMenuOpen] = useState(false);
  const [months, setMonths] = useState<MonthOption[]>([]);
  const [selectedYear, setSelectedYear] = useState<number | null>(null);
  const [selectedMonthKey, setSelectedMonthKey] = useState<string>("");
  const [loading, setLoading] = useState(true);

  const [yearSummaries, setYearSummaries] = useState<Summary[]>([]);
  const [allCategories, setAllCategories] = useState<string[]>([]);
  const [monthlyCategoryData, setMonthlyCategoryData] = useState<
    SummaryCategory[]
  >([]);

  async function loadMonths() {
    const res = await fetch(`${backendUrl}/api/months?family_id=${FAMILY_ID}`);
    const data: MonthOption[] = await res.json();

    setMonths(data);

    if (data.length > 0) {
      const latest = data[0];
      setSelectedYear(latest.year);
      setSelectedMonthKey(`${latest.month}-${latest.year}`);
    }

    setLoading(false);
  }

  async function loadYearData(year: number) {
    const yearMonths = months
      .filter((m) => m.year === year)
      .sort((a, b) => a.month - b.month);

    const summaries: Summary[] = await Promise.all(
      yearMonths.map(async (m) => {
        const res = await fetch(
          `${backendUrl}/api/summary?month=${m.month}&year=${m.year}&family_id=${FAMILY_ID}`
        );
        return res.json();
      })
    );

    setYearSummaries(summaries);

    const categoriesSet = new Set<string>();
    summaries.forEach((summary) => {
      summary.categories.forEach((cat) => categoriesSet.add(cat.category));
    });

    setAllCategories(Array.from(categoriesSet));
  }

  async function loadSingleMonthSummary(month: number, year: number) {
    const res = await fetch(
      `${backendUrl}/api/summary?month=${month}&year=${year}&family_id=${FAMILY_ID}`
    );
    const summary: Summary = await res.json();
    setMonthlyCategoryData(summary.categories);
  }

  useEffect(() => {
    loadMonths();
  }, []);

  useEffect(() => {
    if (selectedYear !== null && months.length > 0) {
      loadYearData(selectedYear);
    }
  }, [selectedYear, months]);

  useEffect(() => {
    if (selectedMonthKey) {
      const [month, year] = selectedMonthKey.split("-").map(Number);
      loadSingleMonthSummary(month, year);
    }
  }, [selectedMonthKey]);

  const availableYears = useMemo(() => {
    return [...new Set(months.map((m) => m.year))].sort((a, b) => b - a);
  }, [months]);

  const monthsInSelectedYear = useMemo(() => {
    if (selectedYear === null) return [];
    return months
      .filter((m) => m.year === selectedYear)
      .sort((a, b) => a.month - b.month);
  }, [months, selectedYear]);

  const annualChartData = useMemo(() => {
    return yearSummaries.map((summary) => {
      const row: ChartRow = {
        monthLabel: monthNames[summary.month] || String(summary.month),
      };

      allCategories.forEach((cat) => {
        row[cat] = 0;
      });

      summary.categories.forEach((cat) => {
        row[cat.category] = cat.amount;
      });

      return row;
    });
  }, [yearSummaries, allCategories]);

  return (
    <main className="relative min-h-screen bg-gradient-to-b from-green-50 via-emerald-50 to-lime-50 text-slate-900">
      {menuOpen && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/30"
            onClick={() => setMenuOpen(false)}
          />
          <div className="fixed right-0 top-0 z-50 h-full w-64 space-y-6 bg-white p-5 shadow-xl">
            <div className="text-xl font-bold text-green-600">תפריט</div>

            <Link
              href={`/?family_id=${FAMILY_ID}`}
              onClick={() => setMenuOpen(false)}
              className="flex items-center gap-2 text-lg"
            >
              <Home size={20} />
              דף הבית
            </Link>

            <Link
              href={`/reports?family_id=${FAMILY_ID}`}
              onClick={() => setMenuOpen(false)}
              className="flex items-center gap-2 text-lg"
            >
              <FileBarChart2 size={20} />
              דוחות
            </Link>
          </div>
        </>
      )}

      <div className="mx-auto max-w-md p-4 space-y-4">
        <div className="flex items-center justify-between">
          <div className="w-10" />
          <h1 className="text-2xl font-bold text-green-600">📊 דוחות</h1>
          <button onClick={() => setMenuOpen(true)} className="p-2">
            <Menu />
          </button>
        </div>

        <div className="space-y-4 rounded-2xl bg-white p-4 shadow-sm">
          <div className="text-right font-semibold">בחירת שנה</div>
          <select
            className="w-full rounded-xl border border-slate-200 p-3 text-right"
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

        <div className="rounded-2xl bg-white p-4 shadow-sm">
          <div className="mb-4 text-right text-lg font-semibold">
            דוח הוצאות שנתי
          </div>

          <div className="h-80">
            {loading ? (
              <div className="text-center text-gray-500">טוען...</div>
            ) : (
              <ResponsiveContainer>
                <BarChart data={annualChartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="monthLabel" />
                  <YAxis />
                  <Tooltip formatter={(value) => formatCurrency(Number(value))} />
                  {allCategories.map((category) => (
                    <Bar
                      key={category}
                      dataKey={category}
                      stackId="a"
                      fill={categoryColors[category] || "#94a3b8"}
                    />
                  ))}
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>

          <div className="mt-4 space-y-2">
            {allCategories.map((category) => (
              <div
                key={category}
                className="flex items-center justify-between rounded-xl bg-slate-50 px-3 py-2"
              >
                <span className="text-sm text-slate-700">{category}</span>
                <span
                  className="h-3 w-3 rounded-full"
                  style={{
                    backgroundColor: categoryColors[category] || "#94a3b8",
                  }}
                />
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-3 rounded-2xl bg-white p-4 shadow-sm">
          <div className="text-right font-semibold">בחירת חודש לדוח חודשי</div>

          <select
            className="w-full rounded-xl border border-slate-200 p-3 text-right"
            value={selectedMonthKey}
            onChange={(e) => setSelectedMonthKey(e.target.value)}
          >
            {monthsInSelectedYear.map((m) => (
              <option key={`${m.month}-${m.year}`} value={`${m.month}-${m.year}`}>
                {m.month}/{m.year}
              </option>
            ))}
          </select>
        </div>

        <div className="rounded-2xl bg-white p-4 shadow-sm">
          <div className="mb-4 text-right text-lg font-semibold">
            דוח הוצאות חודשי לפי קטגוריה
          </div>

          <div className="h-80">
            <ResponsiveContainer>
              <BarChart data={monthlyCategoryData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="category" />
                <YAxis />
                <Tooltip formatter={(value) => formatCurrency(Number(value))} />
                <Bar dataKey="amount">
                  {monthlyCategoryData.map((entry, index) => (
                    <Cell
                      key={index}
                      fill={categoryColors[entry.category] || "#94a3b8"}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </main>
  );
}