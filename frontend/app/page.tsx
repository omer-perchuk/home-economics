"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts";
import {
  Pencil,
  Trash2,
  X,
  Check,
  Home,
  Menu,
  FileBarChart2,
  Edit3,
} from "lucide-react";

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

type Transaction = {
  id: number;
  date: string;
  description: string;
  amount: number;
  category: string;
  type: string;
};

type AppSettings = {
  dashboard_title: string;
};

const categoryColors: Record<string, string> = {
  "סופר וקניות לבית": "#3b82f6",
  "אוכל בחוץ וקפה": "#f59e0b",
  תחבורה: "#10b981",
  "בריאות ופארם": "#ef4444",
  "דיור וחשבונות": "#8b5cf6",
  "בילויים ופנאי": "#ec4899",
  הכנסות: "#22c55e",
  אחר: "#94a3b8",
};

function formatCurrency(value: number) {
  return `₪${value.toLocaleString("he-IL")}`;
}

export default function HomePage() {
  const FAMILY_ID = 1;

  const backendUrl = "https://home-economics.onrender.com";

  const [months, setMonths] = useState<MonthOption[]>([]);
  const [selectedMonth, setSelectedMonth] = useState<MonthOption | null>(null);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);

  const [menuOpen, setMenuOpen] = useState(false);

  async function loadMonths() {
    const res = await fetch(
      `${backendUrl}/api/months?family_id=${FAMILY_ID}`
    );
    const data = await res.json();
    setMonths(data);

    if (data.length > 0) {
      setSelectedMonth(data[0]);
    }
  }

  async function loadData(month: number, year: number) {
    const [summaryRes, txRes] = await Promise.all([
      fetch(
        `${backendUrl}/api/summary?month=${month}&year=${year}&family_id=${FAMILY_ID}`
      ),
      fetch(
        `${backendUrl}/api/transactions?month=${month}&year=${year}&family_id=${FAMILY_ID}`
      ),
    ]);

    const summaryData = await summaryRes.json();
    const txData = await txRes.json();

    setSummary(summaryData);
    setTransactions(txData);
    setLoading(false);
  }

  async function deleteTransaction(id: number) {
    await fetch(`${backendUrl}/api/transactions/${id}`, {
      method: "DELETE",
    });

    if (selectedMonth) {
      loadData(selectedMonth.month, selectedMonth.year);
    }
  }

  useEffect(() => {
    loadMonths();
  }, []);

  useEffect(() => {
    if (selectedMonth) {
      loadData(selectedMonth.month, selectedMonth.year);
    }
  }, [selectedMonth]);

  const chartData = useMemo(() => {
    return summary?.categories ?? [];
  }, [summary]);

  return (
    <main className="min-h-screen bg-green-50 text-slate-900">

      <div className="mx-auto max-w-md p-4 space-y-4">

        <div className="flex items-center justify-between">
          <button onClick={() => setMenuOpen(true)}>
            <Menu />
          </button>

          <h1 className="text-2xl font-bold text-green-600">
            💸 כלכלת הבית
          </h1>

          <div />
        </div>

        <div className="rounded-xl bg-white p-3 shadow">
          <select
            className="w-full rounded-lg border p-2"
            value={
              selectedMonth
                ? `${selectedMonth.month}-${selectedMonth.year}`
                : ""
            }
            onChange={(e) => {
              const [month, year] = e.target.value.split("-").map(Number);
              setSelectedMonth({ month, year });
            }}
          >
            {months.map((m) => (
              <option key={`${m.month}-${m.year}`} value={`${m.month}-${m.year}`}>
                {m.month}/{m.year}
              </option>
            ))}
          </select>
        </div>

        <div className="rounded-xl bg-green-700 text-white p-4">
          <div>סה״כ הוצאות</div>
          <div className="text-3xl font-bold">
            {summary ? formatCurrency(summary.expenses_total) : "₪0"}
          </div>
        </div>

        <div className="rounded-xl bg-white p-4 shadow">

          <div className="h-72">
            <ResponsiveContainer>
              <PieChart>
                <Pie
                  data={chartData}
                  dataKey="amount"
                  nameKey="category"
                  outerRadius={90}
                >
                  {chartData.map((entry, index) => (
                    <Cell
                      key={index}
                      fill={categoryColors[entry.category] || "#94a3b8"}
                    />
                  ))}
                </Pie>

                <Tooltip formatter={(value) => formatCurrency(Number(value))} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="space-y-3">

          <div className="text-lg font-semibold">רשומות</div>

          {loading ? (
            <div>טוען...</div>
          ) : (
            transactions.map((tx) => (
              <div
                key={tx.id}
                className="flex items-center justify-between rounded-xl bg-white p-3 shadow"
              >
                <div>
                  <div className="font-semibold">{tx.description}</div>
                  <div className="text-sm text-gray-500">
                    {tx.date} · {tx.category}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <div className="font-bold">{formatCurrency(tx.amount)}</div>

                  <button onClick={() => deleteTransaction(tx.id)}>
                    <Trash2 size={18} />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </main>
  );
}