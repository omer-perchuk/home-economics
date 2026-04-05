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
  PieChart,
  Pie,
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
  "ביגוד והנעלה": "#f97316",
  "ילדים ומשפחה": "#14b8a6",
  לימודים: "#6366f1",
  "חופשות ונסיעות": "#06b6d4",
  "מתנות ותרומות": "#d946ef",
  ביטוחים: "#64748b",
  "חיות מחמד": "#84cc16",
  משכורת: "#22c55e",
  החזרים: "#0ea5e9",
  הכנסות: "#16a34a",
  אחר: "#94a3b8",
};

function formatCurrency(value: number) {
  return `₪${value.toLocaleString("he-IL", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  })}`;
}

export default function ReportsPage() {
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
  const [authChecked, setAuthChecked] = useState(false);

  function getAccessToken() {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("access_token");
  }

  async function fetchWithAuth(url: string, init?: RequestInit) {
    const token = getAccessToken();

    const res = await fetch(url, {
      ...init,
      headers: {
        ...(init?.headers ?? {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });

    if (res.status === 401) {
      localStorage.removeItem("access_token");
      window.location.href = "/auth";
      throw new Error("Unauthorized");
    }

    return res;
  }

  async function checkAuth() {
    try {
      const token = getAccessToken();

      if (!token) {
        window.location.href = "/auth";
        return;
      }

      const res = await fetchWithAuth(`${backendUrl}/api/me`);
      if (!res.ok) {
        localStorage.removeItem("access_token");
        window.location.href = "/auth";
        return;
      }

      setAuthChecked(true);
    } catch (error) {
      console.error("checkAuth error:", error);
      localStorage.removeItem("access_token");
      window.location.href = "/auth";
    }
  }

  async function loadMonths() {
    try {
      const res = await fetchWithAuth(`${backendUrl}/api/months`);

      if (!res.ok) {
        console.error("loadMonths failed:", res.status, res.statusText);
        setMonths([]);
        setLoading(false);
        return;
      }

      const data = await res.json();

      if (!Array.isArray(data)) {
        console.error("loadMonths expected array but got:", data);
        setMonths([]);
        setLoading(false);
        return;
      }

      setMonths(data);

      if (data.length > 0) {
        const latest = data[0];
        setSelectedYear(latest.year);
        setSelectedMonthKey(`${latest.month}-${latest.year}`);
      }

      setLoading(false);
    } catch (error) {
      console.error("loadMonths error:", error);
      setMonths([]);
      setLoading(false);
    }
  }

  async function loadYearData(year: number) {
    try {
      const yearMonths = months
        .filter((m) => m.year === year)
        .sort((a, b) => a.month - b.month);

      const summaries: Summary[] = await Promise.all(
        yearMonths.map(async (m) => {
          const res = await fetchWithAuth(
            `${backendUrl}/api/summary?month=${m.month}&year=${m.year}`
          );

          if (!res.ok) {
            console.error("loadYearData summary failed:", m, res.status);
            return {
              month: m.month,
              year: m.year,
              expenses_total: 0,
              income_total: 0,
              balance: 0,
              categories: [],
            };
          }

          const json = await res.json();

          return {
            month: Number(json?.month ?? m.month),
            year: Number(json?.year ?? m.year),
            expenses_total: Number(json?.expenses_total ?? 0),
            income_total: Number(json?.income_total ?? 0),
            balance: Number(json?.balance ?? 0),
            categories: Array.isArray(json?.categories) ? json.categories : [],
          };
        })
      );

      setYearSummaries(summaries);

      const categoriesSet = new Set<string>();
      summaries.forEach((summary) => {
        (Array.isArray(summary.categories) ? summary.categories : []).forEach(
          (cat) => categoriesSet.add(cat.category)
        );
      });

      setAllCategories(Array.from(categoriesSet));
    } catch (error) {
      console.error("loadYearData error:", error);
      setYearSummaries([]);
      setAllCategories([]);
    }
  }

  async function loadSingleMonthSummary(month: number, year: number) {
    try {
      const res = await fetchWithAuth(
        `${backendUrl}/api/summary?month=${month}&year=${year}`
      );

      if (!res.ok) {
        console.error(
          "loadSingleMonthSummary failed:",
          res.status,
          res.statusText
        );
        setMonthlyCategoryData([]);
        return;
      }

      const summary = await res.json();

      setMonthlyCategoryData(
        Array.isArray(summary?.categories) ? summary.categories : []
      );
    } catch (error) {
      console.error("loadSingleMonthSummary error:", error);
      setMonthlyCategoryData([]);
    }
  }

  useEffect(() => {
    checkAuth();
  }, []);

  useEffect(() => {
    if (!authChecked) return;
    loadMonths();
  }, [authChecked]);

  useEffect(() => {
    if (!authChecked) return;
    if (selectedYear !== null && months.length > 0) {
      loadYearData(selectedYear);
    }
  }, [selectedYear, months, authChecked]);

  useEffect(() => {
    if (!authChecked) return;
    if (selectedMonthKey) {
      const [month, year] = selectedMonthKey.split("-").map(Number);
      loadSingleMonthSummary(month, year);
    }
  }, [selectedMonthKey, authChecked]);

  const availableYears = useMemo(() => {
    if (!Array.isArray(months)) return [];
    return [...new Set(months.map((m) => m.year))].sort((a, b) => b - a);
  }, [months]);

  const monthsInSelectedYear = useMemo(() => {
    if (selectedYear === null || !Array.isArray(months)) return [];
    return months
      .filter((m) => m.year === selectedYear)
      .sort((a, b) => a.month - b.month);
  }, [months, selectedYear]);

  const annualChartData = useMemo(() => {
    return yearSummaries.map((summary) => {
      const row: ChartRow = {
        monthLabel: monthNames[summary.month] || String(summary.month),
        expenses_total: summary.expenses_total,
        income_total: summary.income_total,
        balance: summary.balance,
      };

      allCategories.forEach((cat) => {
        row[cat] = 0;
      });

      (Array.isArray(summary.categories) ? summary.categories : []).forEach(
        (cat) => {
          row[cat.category] = cat.amount;
        }
      );

      return row;
    });
  }, [yearSummaries, allCategories]);

  const totalYearExpenses = useMemo(() => {
    return yearSummaries.reduce(
      (sum, item) => sum + Number(item.expenses_total || 0),
      0
    );
  }, [yearSummaries]);

  const totalYearIncome = useMemo(() => {
    return yearSummaries.reduce(
      (sum, item) => sum + Number(item.income_total || 0),
      0
    );
  }, [yearSummaries]);

  const totalYearBalance = useMemo(() => {
    return yearSummaries.reduce(
      (sum, item) => sum + Number(item.balance || 0),
      0
    );
  }, [yearSummaries]);

  const mostExpensiveMonth = useMemo(() => {
    if (!yearSummaries.length) return null;
    return yearSummaries.reduce((max, current) =>
      current.expenses_total > max.expenses_total ? current : max
    );
  }, [yearSummaries]);

  const topMonthCategory = useMemo(() => {
    if (!monthlyCategoryData.length) return null;
    return monthlyCategoryData.reduce((max, current) =>
      current.amount > max.amount ? current : max
    );
  }, [monthlyCategoryData]);

  if (!authChecked) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-gradient-to-b from-green-50 via-emerald-50 to-lime-50 text-slate-900">
        <div className="text-lg font-medium">טוען...</div>
      </main>
    );
  }

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

      <div className="mx-auto max-w-md space-y-4 p-4">
        <div className="flex items-center justify-between">
          <div className="w-10" />
          <h1 className="text-2xl font-bold text-green-600">📊 דוחות</h1>
          <button onClick={() => setMenuOpen(true)} className="p-2">
            <Menu />
          </button>
        </div>

        <div className="grid grid-cols-3 gap-3">
          <div className="rounded-2xl bg-white p-3 text-center shadow-sm">
            <div className="text-xs text-slate-500">סה״כ הוצאות</div>
            <div className="mt-1 text-sm font-bold text-red-500">
              {formatCurrency(totalYearExpenses)}
            </div>
          </div>

          <div className="rounded-2xl bg-white p-3 text-center shadow-sm">
            <div className="text-xs text-slate-500">סה״כ הכנסות</div>
            <div className="mt-1 text-sm font-bold text-green-600">
              {formatCurrency(totalYearIncome)}
            </div>
          </div>

          <div className="rounded-2xl bg-white p-3 text-center shadow-sm">
            <div className="text-xs text-slate-500">מאזן</div>
            <div
              className={`mt-1 text-sm font-bold ${
                totalYearBalance >= 0 ? "text-emerald-600" : "text-rose-500"
              }`}
            >
              {formatCurrency(totalYearBalance)}
            </div>
          </div>
        </div>

        {mostExpensiveMonth && (
          <div className="rounded-2xl bg-white p-4 text-right shadow-sm">
            <div className="text-sm text-slate-500">החודש הכי יקר השנה</div>
            <div className="mt-1 text-lg font-bold text-slate-900">
              🔥 {mostExpensiveMonth.month}/{mostExpensiveMonth.year}
            </div>
            <div className="mt-1 text-sm text-slate-600">
              {formatCurrency(mostExpensiveMonth.expenses_total)}
            </div>
          </div>
        )}

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
            סה״כ הוצאות לפי חודש
          </div>

          <div className="h-72">
            {loading ? (
              <div className="text-center text-gray-500">טוען...</div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={annualChartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="monthLabel" />
                  <YAxis />
                  <Tooltip formatter={(value) => formatCurrency(Number(value))} />
                  <Bar dataKey="expenses_total" fill="#16a34a" radius={[10, 10, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        <div className="rounded-2xl bg-white p-4 shadow-sm">
          <div className="mb-4 text-right text-lg font-semibold">
            דוח הוצאות שנתי לפי קטגוריות
          </div>

          <div className="h-80">
            {loading ? (
              <div className="text-center text-gray-500">טוען...</div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
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

        {topMonthCategory && (
          <div className="rounded-2xl bg-white p-4 text-right shadow-sm">
            <div className="text-sm text-slate-500">הקטגוריה המובילה בחודש שנבחר</div>
            <div className="mt-1 text-lg font-bold text-slate-900">
              {topMonthCategory.category}
            </div>
            <div className="mt-1 text-sm text-slate-600">
              {formatCurrency(topMonthCategory.amount)}
            </div>
          </div>
        )}

        <div className="rounded-2xl bg-white p-4 shadow-sm">
          <div className="mb-4 text-right text-lg font-semibold">
            התפלגות חודשית לפי קטגוריה
          </div>

          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={Array.isArray(monthlyCategoryData) ? monthlyCategoryData : []}
                  dataKey="amount"
                  nameKey="category"
                  cx="50%"
                  cy="50%"
                  outerRadius={95}
                  innerRadius={45}
                  paddingAngle={3}
                  stroke="#ffffff"
                  strokeWidth={2}
                >
                  {(Array.isArray(monthlyCategoryData) ? monthlyCategoryData : []).map(
                    (entry, index) => (
                      <Cell
                        key={index}
                        fill={categoryColors[entry.category] || "#94a3b8"}
                      />
                    )
                  )}
                </Pie>
                <Tooltip formatter={(value) => formatCurrency(Number(value))} />
              </PieChart>
            </ResponsiveContainer>
          </div>

          <div className="mt-4 space-y-2">
            {(Array.isArray(monthlyCategoryData) ? monthlyCategoryData : []).map(
              (item) => (
                <div
                  key={item.category}
                  className="flex items-center justify-between rounded-xl bg-slate-50 px-3 py-2"
                >
                  <span className="text-sm font-semibold text-slate-900">
                    {formatCurrency(item.amount)}
                  </span>

                  <div className="flex items-center gap-2">
                    <span className="text-sm text-slate-700">{item.category}</span>
                    <span
                      className="h-3 w-3 rounded-full"
                      style={{
                        backgroundColor:
                          categoryColors[item.category] || "#94a3b8",
                      }}
                    />
                  </div>
                </div>
              )
            )}
          </div>
        </div>

        <div className="rounded-2xl bg-white p-4 shadow-sm">
          <div className="mb-4 text-right text-lg font-semibold">
            דוח חודשי לפי קטגוריה - עמודות
          </div>

          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={Array.isArray(monthlyCategoryData) ? monthlyCategoryData : []}
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="category" />
                <YAxis />
                <Tooltip formatter={(value) => formatCurrency(Number(value))} />
                <Bar dataKey="amount" radius={[10, 10, 0, 0]}>
                  {(Array.isArray(monthlyCategoryData) ? monthlyCategoryData : []).map(
                    (entry, index) => (
                      <Cell
                        key={index}
                        fill={categoryColors[entry.category] || "#94a3b8"}
                      />
                    )
                  )}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </main>
  );
}