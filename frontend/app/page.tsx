"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
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

type PieClickData = {
  category?: string;
  amount?: number;
  value?: number;
  name?: string;
  payload?: {
    category?: string;
    amount?: number;
  };
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
  "הכנסות": "#22c55e",
  "אחר": "#94a3b8",
};

function formatCurrency(value: number) {
  return `₪${value.toLocaleString("he-IL", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  })}`;
}

export default function HomePage() {
  const searchParams = useSearchParams();

  const [mounted, setMounted] = useState(false);
  const [familySlug, setFamilySlug] = useState<string>("");

  const [menuOpen, setMenuOpen] = useState(false);
  const [months, setMonths] = useState<MonthOption[]>([]);
  const [selectedMonth, setSelectedMonth] = useState<MonthOption | null>(null);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [editingId, setEditingId] = useState<number | null>(null);
  const [expandedCategory, setExpandedCategory] = useState<string | null>(null);

  const [clickedSliceInfo, setClickedSliceInfo] = useState<SummaryCategory | null>(null);
  const clickInfoTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const [title, setTitle] = useState("כלכלת הבית");
  const [titleDraft, setTitleDraft] = useState("כלכלת הבית");
  const [isEditingTitle, setIsEditingTitle] = useState(false);

  const [editForm, setEditForm] = useState({
    description: "",
    amount: "",
    category: "",
    type: "expense",
  });

  const backendUrl = "https://home-economics.onrender.com";
  const familyQuery = `family=${encodeURIComponent(familySlug || "omer-family")}`;

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    const slug = searchParams.get("family") || "omer-family";
    setFamilySlug(slug);
  }, [searchParams]);

  useEffect(() => {
    return () => {
      if (clickInfoTimeoutRef.current) {
        clearTimeout(clickInfoTimeoutRef.current);
      }
    };
  }, []);

  async function loadSettings() {
    const res = await fetch(`${backendUrl}/api/settings`);
    const data: AppSettings = await res.json();
    setTitle(data.dashboard_title);
    setTitleDraft(data.dashboard_title);
  }

  async function loadMonths(currentFamilySlug: string) {
    try {
      setError("");
      setLoading(true);

      const res = await fetch(
        `${backendUrl}/api/months?family_slug=${encodeURIComponent(currentFamilySlug)}`
      );
      const data: MonthOption[] = await res.json();

      setMonths(data);

      if (data.length > 0) {
        setSelectedMonth(data[0]);
      } else {
        setSelectedMonth(null);
        setSummary(null);
        setTransactions([]);
        setLoading(false);
      }
    } catch (err) {
      setError(String(err));
      setLoading(false);
    }
  }

  async function loadData(month: number, year: number, currentFamilySlug: string) {
    try {
      setLoading(true);
      setError("");

      const [summaryRes, txRes] = await Promise.all([
        fetch(
          `${backendUrl}/api/summary?month=${month}&year=${year}&family_slug=${encodeURIComponent(currentFamilySlug)}`
        ),
        fetch(
          `${backendUrl}/api/transactions?month=${month}&year=${year}&family_slug=${encodeURIComponent(currentFamilySlug)}`
        ),
      ]);

      const summaryData = await summaryRes.json();
      const txData = await txRes.json();

      setSummary(summaryData);
      setTransactions(txData);
      setExpandedCategory(null);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  async function deleteTransaction(id: number) {
    try {
      setError("");
      await fetch(`${backendUrl}/api/transactions/${id}`, {
        method: "DELETE",
      });

      if (selectedMonth && familySlug) {
        loadData(selectedMonth.month, selectedMonth.year, familySlug);
      }
    } catch (err) {
      setError(String(err));
    }
  }

  async function updateTransaction(id: number) {
    try {
      setError("");
      await fetch(`${backendUrl}/api/transactions/${id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          description: editForm.description,
          amount: Number(editForm.amount),
          category: editForm.category,
          type: editForm.type,
        }),
      });

      setEditingId(null);

      if (selectedMonth && familySlug) {
        loadData(selectedMonth.month, selectedMonth.year, familySlug);
      }
    } catch (err) {
      setError(String(err));
    }
  }

  function startEdit(tx: Transaction) {
    setEditingId(tx.id);
    setEditForm({
      description: tx.description,
      amount: String(tx.amount),
      category: tx.category,
      type: tx.type,
    });
  }

  function cancelEdit() {
    setEditingId(null);
  }

  function startTitleEdit() {
    setTitleDraft(title);
    setIsEditingTitle(true);
  }

  async function saveTitle() {
    try {
      await fetch(`${backendUrl}/api/settings/title`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          dashboard_title: titleDraft,
        }),
      });

      setTitle(titleDraft);
      setIsEditingTitle(false);
    } catch (err) {
      setError(String(err));
    }
  }

  function getCategoryTransactions(category: string) {
    return transactions.filter((tx) => tx.category === category);
  }

  function handlePieClick(data: PieClickData) {
    const category = data.category ?? data.payload?.category ?? data.name;
    const amount = data.amount ?? data.payload?.amount ?? data.value;

    if (!category || amount === undefined) {
      return;
    }

    setExpandedCategory((prev) => (prev === category ? null : category));
    setClickedSliceInfo({
      category,
      amount: Number(amount),
    });

    if (clickInfoTimeoutRef.current) {
      clearTimeout(clickInfoTimeoutRef.current);
    }

    clickInfoTimeoutRef.current = setTimeout(() => {
      setClickedSliceInfo(null);
    }, 5000);
  }

  useEffect(() => {
    if (mounted) {
      loadSettings();
    }
  }, [mounted]);

  useEffect(() => {
    if (mounted && familySlug) {
      loadMonths(familySlug);
    }
  }, [mounted, familySlug]);

  useEffect(() => {
    if (selectedMonth && familySlug) {
      loadData(selectedMonth.month, selectedMonth.year, familySlug);
    }
  }, [selectedMonth, familySlug]);

  const chartData = useMemo(() => {
    return summary?.categories ?? [];
  }, [summary]);

  if (!mounted) return null;

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
              href={`/?${familyQuery}`}
              onClick={() => setMenuOpen(false)}
              className="flex items-center gap-2 text-lg"
            >
              <Home size={20} />
              דף הבית
            </Link>

            <Link
              href={`/reports?${familyQuery}`}
              onClick={() => setMenuOpen(false)}
              className="flex items-center gap-2 text-lg"
            >
              <FileBarChart2 size={20} />
              דוחות
            </Link>
          </div>
        </>
      )}

      <div className="relative mx-auto max-w-md p-4 space-y-4">
        <div className="sticky top-0 z-30 flex items-center justify-between bg-green-50/95 px-2 py-2 backdrop-blur">
          <button onClick={() => setMenuOpen(true)} className="p-2">
            <Menu size={28} />
          </button>

          {isEditingTitle ? (
            <div className="flex items-center gap-2">
              <input
                value={titleDraft}
                onChange={(e) => setTitleDraft(e.target.value)}
                className="rounded-lg border px-2 py-1"
              />

              <button onClick={saveTitle}>
                <Check size={18} />
              </button>

              <button onClick={() => setIsEditingTitle(false)}>
                <X size={18} />
              </button>
            </div>
          ) : (
            <h1 className="flex items-center gap-2 text-2xl font-bold text-green-600">
              <span>💸</span>
              <span>{title}</span>
              <button onClick={startTitleEdit} className="text-green-700">
                <Edit3 size={18} />
              </button>
            </h1>
          )}

          <div />
        </div>

        <div className="rounded-xl bg-blue-50 px-3 py-2 text-sm text-blue-800 shadow-sm">
          משפחה פעילה: <strong>{familySlug || "לא נטען"}</strong>
        </div>

        {error && (
          <div className="rounded-2xl bg-red-50 p-4 text-sm text-red-700 shadow-sm">
            {error}
          </div>
        )}

        <div className="rounded-xl bg-white p-3 shadow">
          <select
            className="w-full rounded-lg border p-2"
            value={
              selectedMonth ? `${selectedMonth.month}-${selectedMonth.year}` : ""
            }
            onChange={(e) => {
              const [month, year] = e.target.value.split("-").map(Number);
              setSelectedMonth({ month, year });
            }}
          >
            {months.map((m) => (
              <option key={`${m.month}-${m.year}`} value={`${m.month}-${m.year}`}>
                {monthNames[m.month]} {m.year}
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
          <div className="mb-3 font-semibold">חלוקה לקטגוריות</div>

          {clickedSliceInfo && (
            <div className="mb-3 rounded-xl bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
              <div className="font-semibold">{clickedSliceInfo.category}</div>
              <div>{formatCurrency(clickedSliceInfo.amount)}</div>
            </div>
          )}

          <div className="h-72">
            <ResponsiveContainer>
              <PieChart>
                <Pie
                  data={chartData}
                  dataKey="amount"
                  nameKey="category"
                  outerRadius={90}
                  label={({ value, percent }) =>
                    `${formatCurrency(Number(value))} (${((percent ?? 0) * 100).toFixed(0)}%)`
                  }
                  labelLine
                  onClick={(data) => handlePieClick(data as PieClickData)}
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

          <div className="mt-4 space-y-2">
            {chartData.map((item) => {
              const isOpen = expandedCategory === item.category;
              const categoryTransactions = getCategoryTransactions(item.category);

              return (
                <div key={item.category} className="rounded-xl bg-slate-100">
                  <button
                    onClick={() =>
                      setExpandedCategory((prev) =>
                        prev === item.category ? null : item.category
                      )
                    }
                    className={`flex w-full items-center justify-between px-3 py-3 ${
                      isOpen ? "bg-slate-200" : ""
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <span
                        className="h-3 w-3 rounded-full"
                        style={{
                          backgroundColor:
                            categoryColors[item.category] || "#94a3b8",
                        }}
                      />
                      <span>{item.category}</span>
                    </div>

                    <span>{formatCurrency(item.amount)}</span>
                  </button>

                  {isOpen && (
                    <div className="space-y-2 px-3 pb-3">
                      {categoryTransactions.length === 0 ? (
                        <div className="rounded-xl bg-white px-3 py-2 text-sm text-slate-500">
                          אין רשומות בקטגוריה הזו.
                        </div>
                      ) : (
                        categoryTransactions.map((tx) => (
                          <div
                            key={tx.id}
                            className="flex items-center justify-between rounded-xl bg-white px-3 py-2 text-sm"
                          >
                            <div>
                              <div className="font-medium">{tx.description}</div>
                              <div className="text-slate-500">{tx.date}</div>
                            </div>

                            <div className="font-semibold">
                              {formatCurrency(tx.amount)}
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        <div className="space-y-3">
          <div className="text-lg font-semibold">רשומות</div>

          {loading ? (
            <div className="text-sm text-slate-500">טוען נתונים...</div>
          ) : (
            transactions.map((tx) => (
              <div
                key={tx.id}
                className="flex items-center justify-between rounded-xl bg-white p-3 shadow"
              >
                {editingId === tx.id ? (
                  <div className="w-full space-y-2">
                    <input
                      className="w-full rounded-lg border p-2"
                      value={editForm.description}
                      onChange={(e) =>
                        setEditForm({ ...editForm, description: e.target.value })
                      }
                    />

                    <input
                      className="w-full rounded-lg border p-2"
                      type="number"
                      value={editForm.amount}
                      onChange={(e) =>
                        setEditForm({ ...editForm, amount: e.target.value })
                      }
                    />

                    <input
                      className="w-full rounded-lg border p-2"
                      value={editForm.category}
                      onChange={(e) =>
                        setEditForm({ ...editForm, category: e.target.value })
                      }
                    />

                    <select
                      className="w-full rounded-lg border p-2"
                      value={editForm.type}
                      onChange={(e) =>
                        setEditForm({ ...editForm, type: e.target.value })
                      }
                    >
                      <option value="expense">expense</option>
                      <option value="income">income</option>
                    </select>

                    <div className="flex gap-2">
                      <button
                        onClick={() => updateTransaction(tx.id)}
                        className="rounded-lg border border-green-200 bg-green-50 p-2 text-green-700"
                      >
                        <Check size={18} />
                      </button>

                      <button
                        onClick={cancelEdit}
                        className="rounded-lg border border-slate-200 p-2 text-slate-600"
                      >
                        <X size={18} />
                      </button>
                    </div>
                  </div>
                ) : (
                  <>
                    <div>
                      <div className="font-semibold">{tx.description}</div>
                      <div className="text-sm text-gray-500">
                        {tx.date} · {tx.category}
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <div className="font-bold">{formatCurrency(tx.amount)}</div>

                      <button onClick={() => startEdit(tx)} className="p-2">
                        <Pencil size={18} />
                      </button>

                      <button onClick={() => deleteTransaction(tx.id)} className="p-2">
                        <Trash2 size={18} />
                      </button>
                    </div>
                  </>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </main>
  );
}