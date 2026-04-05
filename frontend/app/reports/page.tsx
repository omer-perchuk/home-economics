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
  return `₪${value.toLocaleString("he-IL")}`;
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

  // 🔥 קריאת token
  function getAccessToken() {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("access_token");
  }

  // 🔥 fetch עם auth
  async function fetchWithAuth(url: string) {
    const token = getAccessToken();

    const res = await fetch(url, {
      headers: {
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

  async function loadMonths() {
    try {
      const res = await fetchWithAuth(`${backendUrl}/api/months`);

      const data = await res.json();
      setMonths(data);

      if (data.length > 0) {
        const latest = data[0];
        setSelectedYear(latest.year);
        setSelectedMonthKey(`${latest.month}-${latest.year}`);
      }

      setLoading(false);
    } catch (error) {
      console.error("loadMonths error:", error);
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

          const json = await res.json();

          return {
            month: json.month,
            year: json.year,
            expenses_total: json.expenses_total,
            income_total: json.income_total,
            balance: json.balance,
            categories: json.categories || [],
          };
        })
      );

      setYearSummaries(summaries);

      const categoriesSet = new Set<string>();
      summaries.forEach((s) =>
        s.categories.forEach((c) => categoriesSet.add(c.category))
      );

      setAllCategories(Array.from(categoriesSet));
    } catch (error) {
      console.error("loadYearData error:", error);
    }
  }

  async function loadSingleMonthSummary(month: number, year: number) {
    try {
      const res = await fetchWithAuth(
        `${backendUrl}/api/summary?month=${month}&year=${year}`
      );

      const summary = await res.json();

      setMonthlyCategoryData(summary.categories || []);
    } catch (error) {
      console.error("loadSingleMonthSummary error:", error);
    }
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
      <div className="mx-auto max-w-md space-y-4 p-4">
        <h1 className="text-2xl font-bold text-green-600 text-center">
          📊 דוחות
        </h1>

        <select
          className="w-full rounded-xl border p-3"
          value={selectedYear ?? ""}
          onChange={(e) => setSelectedYear(Number(e.target.value))}
        >
          {availableYears.map((year) => (
            <option key={year}>{year}</option>
          ))}
        </select>

        <div className="h-80 bg-white p-4 rounded-2xl">
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
        </div>
      </div>
    </main>
  );
}