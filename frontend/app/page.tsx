"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts";
import {
  Pencil,
  Trash2,
  X,
  Check,
  Edit3,
  Plus,
  Menu,
  Home,
  FileBarChart2,
  CalendarDays,
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

type PieLabelProps = {
  cx?: number;
  cy?: number;
  midAngle?: number;
  outerRadius?: number;
  percent?: number;
  value?: number;
};

type PieClickData = {
  category?: string;
  name?: string;
  payload?: {
    category?: string;
  };
};

type MeResponse = {
  user_id: number;
  family_id: number;
};

type ViewType = "expense" | "income";

type SummaryCategoryWithType = SummaryCategory & {
  resolvedType: ViewType;
};

const RADIAN = Math.PI / 180;

const categories = [
  "סופר וקניות לבית",
  "אוכל בחוץ וקפה",
  "תחבורה",
  "בריאות ופארם",
  "דיור וחשבונות",
  "בילויים ופנאי",
  "ביגוד והנעלה",
  "ילדים ומשפחה",
  "לימודים",
  "חופשות ונסיעות",
  "מתנות ותרומות",
  "ביטוחים",
  "חיות מחמד",
  "משכורת",
  "החזרים",
  "הכנסות",
  "אחר",
];

const incomeCategories = new Set(["משכורת", "החזרים", "הכנסות"]);

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
  return `₪${value.toLocaleString("he-IL")}`;
}

function getDaysInMonth(month: number, year: number) {
  return new Date(year, month, 0).getDate();
}

function resolveCategoryType(category: string): ViewType {
  return incomeCategories.has(category) ? "income" : "expense";
}

export default function HomePage() {
  const router = useRouter();

  const backendUrl =
    process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  function getAccessToken() {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("access_token");
  }

  const [menuOpen, setMenuOpen] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [authChecked, setAuthChecked] = useState(false);

  const [months, setMonths] = useState<MonthOption[]>([]);
  const [selectedMonth, setSelectedMonth] = useState<MonthOption | null>(null);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);

  const [editing, setEditing] = useState<Transaction | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);

  const [editDescription, setEditDescription] = useState("");
  const [editAmount, setEditAmount] = useState(0);
  const [editCategory, setEditCategory] = useState("");
  const [editType, setEditType] = useState("expense");
  const [editDay, setEditDay] = useState(1);
  const [editMonth, setEditMonth] = useState(1);

  const [newDescription, setNewDescription] = useState("");
  const [newAmount, setNewAmount] = useState(0);
  const [newCategory, setNewCategory] = useState(categories[0]);
  const [newType, setNewType] = useState("expense");
  const [newDay, setNewDay] = useState(1);
  const [newMonth, setNewMonth] = useState(1);

  const [title, setTitle] = useState("כלכלת הבית");
  const [titleDraft, setTitleDraft] = useState("כלכלת הבית");
  const [isEditingTitle, setIsEditingTitle] = useState(false);

  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [viewType, setViewType] = useState<ViewType>("expense");

  async function fetchWithAuth(input: string, init?: RequestInit) {
    const token = getAccessToken();

    const res = await fetch(input, {
      ...init,
      headers: {
        ...(init?.headers ?? {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });

    if (res.status === 401) {
      localStorage.removeItem("access_token");
      router.replace("/auth");
      throw new Error("Not authenticated");
    }

    return res;
  }

  async function checkSession() {
    try {
      const token = getAccessToken();

      if (!token) {
        router.replace("/auth");
        return;
      }

      const res = await fetch(`${backendUrl}/api/me`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!res.ok) {
        localStorage.removeItem("access_token");
        router.replace("/auth");
        return;
      }

      const data: MeResponse = await res.json();

      if (!data?.user_id || !data?.family_id) {
        localStorage.removeItem("access_token");
        router.replace("/auth");
        return;
      }

      setIsAuthenticated(true);
    } catch (error) {
      console.error("checkSession error:", error);
      localStorage.removeItem("access_token");
      router.replace("/auth");
    } finally {
      setAuthChecked(true);
    }
  }

  async function loadSettings() {
    try {
      const res = await fetchWithAuth(`${backendUrl}/api/settings`);

      if (!res.ok) {
        console.error("loadSettings failed:", res.status, res.statusText);
        setTitle("כלכלת הבית");
        setTitleDraft("כלכלת הבית");
        return;
      }

      const data = await res.json();

      setTitle(
        typeof data?.dashboard_title === "string" && data.dashboard_title.trim()
          ? data.dashboard_title
          : "כלכלת הבית"
      );
      setTitleDraft(
        typeof data?.dashboard_title === "string" && data.dashboard_title.trim()
          ? data.dashboard_title
          : "כלכלת הבית"
      );
    } catch (error) {
      console.error("loadSettings error:", error);
      setTitle("כלכלת הבית");
      setTitleDraft("כלכלת הבית");
    }
  }

  async function saveTitle() {
    try {
      const res = await fetchWithAuth(`${backendUrl}/api/settings/title`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          dashboard_title: titleDraft,
        }),
      });

      if (!res.ok) {
        console.error("saveTitle failed:", res.status, res.statusText);
        return;
      }

      setTitle(titleDraft || "כלכלת הבית");
      setIsEditingTitle(false);
    } catch (error) {
      console.error("saveTitle error:", error);
    }
  }

  async function loadMonths() {
    try {
      const res = await fetchWithAuth(`${backendUrl}/api/months`);

      if (!res.ok) {
        console.error("loadMonths failed:", res.status, res.statusText);
        setMonths([]);
        return;
      }

      const data = await res.json();

      if (!Array.isArray(data)) {
        console.error("loadMonths expected array but got:", data);
        setMonths([]);
        return;
      }

      setMonths(data);

      if (data.length > 0) {
        setSelectedMonth((prev) => prev ?? data[0]);
        setNewMonth(data[0].month);
      }
    } catch (error) {
      console.error("loadMonths error:", error);
      setMonths([]);
    }
  }

  async function loadData(month: number, year: number) {
    try {
      setLoading(true);

      const [summaryRes, txRes] = await Promise.all([
        fetchWithAuth(`${backendUrl}/api/summary?month=${month}&year=${year}`),
        fetchWithAuth(
          `${backendUrl}/api/transactions?month=${month}&year=${year}`
        ),
      ]);

      let summaryData: Summary | null = null;
      let txData: Transaction[] = [];

      if (summaryRes.ok) {
        const json = await summaryRes.json();
        summaryData = {
          month: Number(json?.month ?? month),
          year: Number(json?.year ?? year),
          expenses_total: Number(json?.expenses_total ?? 0),
          income_total: Number(json?.income_total ?? 0),
          balance: Number(json?.balance ?? 0),
          categories: Array.isArray(json?.categories) ? json.categories : [],
        };
      } else {
        console.error("loadData summary failed:", summaryRes.status);
        summaryData = {
          month,
          year,
          expenses_total: 0,
          income_total: 0,
          balance: 0,
          categories: [],
        };
      }

      if (txRes.ok) {
        const json = await txRes.json();
        txData = Array.isArray(json) ? json : [];
      } else {
        console.error("loadData transactions failed:", txRes.status);
        txData = [];
      }

      setSummary(summaryData);
      setTransactions(txData);
      setSelectedCategory(null);
    } catch (error) {
      console.error("loadData error:", error);
      setSummary({
        month,
        year,
        expenses_total: 0,
        income_total: 0,
        balance: 0,
        categories: [],
      });
      setTransactions([]);
      setSelectedCategory(null);
    } finally {
      setLoading(false);
    }
  }

  async function deleteTransaction(id: number) {
    try {
      const res = await fetchWithAuth(`${backendUrl}/api/transactions/${id}`, {
        method: "DELETE",
      });

      if (!res.ok) {
        console.error("deleteTransaction failed:", res.status, res.statusText);
        return;
      }

      if (selectedMonth) {
        loadData(selectedMonth.month, selectedMonth.year);
      }
    } catch (error) {
      console.error("deleteTransaction error:", error);
    }
  }

  function openEdit(tx: Transaction) {
    setEditing(tx);
    setEditDescription(tx.description);
    setEditAmount(tx.amount);
    setEditCategory(tx.category);
    setEditType(tx.type);

    const [dayStr, monthStr] = tx.date.split("/");
    setEditDay(Number(dayStr));
    setEditMonth(Number(monthStr));
  }

  async function saveEdit() {
    if (!editing || !selectedMonth) return;

    try {
      const res = await fetchWithAuth(
        `${backendUrl}/api/transactions/${editing.id}`,
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            description: editDescription,
            amount: editAmount,
            category: editCategory,
            type: editType,
            day: editDay,
            month: editMonth,
            year: selectedMonth.year,
          }),
        }
      );

      if (!res.ok) {
        console.error("saveEdit failed:", res.status, res.statusText);
        return;
      }

      setEditing(null);
      loadData(selectedMonth.month, selectedMonth.year);
      loadMonths();
    } catch (error) {
      console.error("saveEdit error:", error);
    }
  }

  async function createTransaction() {
    if (!selectedMonth) return;

    try {
      const res = await fetchWithAuth(`${backendUrl}/api/transactions`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          description: newDescription,
          amount: newAmount,
          category: newCategory,
          type: newType,
          day: newDay,
          month: newMonth,
          year: selectedMonth.year,
        }),
      });

      if (!res.ok) {
        console.error("createTransaction failed:", res.status, res.statusText);
        return;
      }

      setShowCreateModal(false);
      setNewDescription("");
      setNewAmount(0);
      setNewCategory(categories[0]);
      setNewType("expense");
      setNewDay(1);
      setNewMonth(selectedMonth.month);

      loadMonths();
      loadData(selectedMonth.month, selectedMonth.year);
    } catch (error) {
      console.error("createTransaction error:", error);
    }
  }

  function renderCustomLabel({
    cx = 0,
    cy = 0,
    midAngle = 0,
    outerRadius = 0,
    percent = 0,
    value = 0,
  }: PieLabelProps) {
    if (percent < 0.05) return null;

    const sin = Math.sin(-RADIAN * midAngle);
    const cos = Math.cos(-RADIAN * midAngle);

    const sx = cx + (outerRadius + 6) * cos;
    const sy = cy + (outerRadius + 6) * sin;

    const mx = cx + (outerRadius + 22) * cos;
    const my = cy + (outerRadius + 22) * sin;

    const ex = mx + (cos >= 0 ? 18 : -18);
    const ey = my;

    const textAnchor = cos >= 0 ? "start" : "end";

    return (
      <g>
        <path
          d={`M${sx},${sy} L${mx},${my} L${ex},${ey}`}
          stroke="#94a3b8"
          fill="none"
          strokeWidth={1.5}
        />
        <circle cx={ex} cy={ey} r={2} fill="#94a3b8" />
        <text
          x={ex + (cos >= 0 ? 6 : -6)}
          y={ey - 2}
          textAnchor={textAnchor}
          fill="#0f172a"
          fontSize={12}
          fontWeight={700}
        >
          {formatCurrency(Number(value))}
        </text>
        <text
          x={ex + (cos >= 0 ? 6 : -6)}
          y={ey + 14}
          textAnchor={textAnchor}
          fill="#64748b"
          fontSize={11}
        >
          {`${(percent * 100).toFixed(0)}%`}
        </text>
      </g>
    );
  }

  function toggleCategory(category: string) {
    setSelectedCategory((prev) => (prev === category ? null : category));
  }

  function handlePieClick(data: PieClickData) {
    const category = data.category ?? data.payload?.category ?? data.name;
    if (!category) return;
    toggleCategory(category);
  }

  useEffect(() => {
    checkSession();
  }, []);

  useEffect(() => {
    if (!isAuthenticated) return;
    loadMonths();
    loadSettings();
  }, [isAuthenticated]);

  useEffect(() => {
    if (selectedMonth && isAuthenticated) {
      loadData(selectedMonth.month, selectedMonth.year);
      setNewMonth(selectedMonth.month);
    }
  }, [selectedMonth, isAuthenticated]);

  useEffect(() => {
    setSelectedCategory(null);
  }, [viewType]);

  const normalizedCategories = useMemo<SummaryCategoryWithType[]>(() => {
    if (!Array.isArray(summary?.categories)) return [];

    return summary.categories.map((item) => ({
      ...item,
      resolvedType: resolveCategoryType(item.category),
    }));
  }, [summary]);

  const chartData = useMemo(() => {
    return normalizedCategories.filter(
      (item) => item.resolvedType === viewType
    );
  }, [normalizedCategories, viewType]);

  const displayedTotal = useMemo(() => {
    if (!summary) return 0;
    return viewType === "expense"
      ? summary.expenses_total
      : summary.income_total;
  }, [summary, viewType]);

  const filteredTransactions = useMemo(() => {
    const safeTransactions = Array.isArray(transactions) ? transactions : [];

    const byType = safeTransactions.filter((tx) => tx.type === viewType);

    const filtered = !selectedCategory
      ? byType
      : byType.filter((tx) => tx.category === selectedCategory);

    return [...filtered].sort((a, b) => {
      const [dayA, monthA] = a.date.split("/").map(Number);
      const [dayB, monthB] = b.date.split("/").map(Number);

      const yearA = selectedMonth?.year ?? new Date().getFullYear();
      const yearB = selectedMonth?.year ?? new Date().getFullYear();

      const dateA = new Date(yearA, monthA - 1, dayA).getTime();
      const dateB = new Date(yearB, monthB - 1, dayB).getTime();

      return dateB - dateA;
    });
  }, [transactions, selectedCategory, selectedMonth, viewType]);

  if (!authChecked || !isAuthenticated) {
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
          <div className="w-10">
            {!isEditingTitle && (
              <button
                onClick={() => setIsEditingTitle(true)}
                className="text-gray-400 hover:text-blue-600"
              >
                <Edit3 size={16} />
              </button>
            )}
          </div>

          <div className="flex items-center gap-2">
            {isEditingTitle ? (
              <>
                <input
                  value={titleDraft}
                  onChange={(e) => setTitleDraft(e.target.value)}
                  className="rounded-lg border border-slate-300 px-3 py-1.5 shadow-sm"
                />
                <button onClick={saveTitle} className="text-green-600">
                  <Check size={18} />
                </button>
                <button
                  onClick={() => {
                    setTitleDraft(title);
                    setIsEditingTitle(false);
                  }}
                  className="text-gray-500"
                >
                  <X size={18} />
                </button>
              </>
            ) : (
              <h1 className="text-2xl font-bold text-green-600">💸 {title}</h1>
            )}
          </div>

          <button onClick={() => setMenuOpen(true)} className="p-2">
            <Menu />
          </button>
        </div>

        <div className="rounded-[2rem] border border-white/70 bg-white/90 p-4 shadow-[0_12px_30px_rgba(16,185,129,0.10)] backdrop-blur">
          <div className="mb-3 flex items-center justify-end gap-2 text-sm font-medium text-slate-500">
            <span>בחירת חודש</span>
            <CalendarDays size={16} />
          </div>

          <div className="rounded-2xl border border-emerald-100 bg-gradient-to-r from-white to-emerald-50 px-3 py-2 shadow-inner">
            <select
              className="w-full bg-transparent px-1 py-2 text-right text-base font-semibold text-slate-700 outline-none"
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
              {(Array.isArray(months) ? months : []).map((m) => (
                <option
                  key={`${m.month}-${m.year}`}
                  value={`${m.month}-${m.year}`}
                >
                  {m.month}/{m.year}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="rounded-[2rem] bg-white p-2 shadow-[0_12px_30px_rgba(15,23,42,0.08)]">
          <div className="grid grid-cols-2 gap-2 rounded-[1.4rem] bg-slate-100 p-1">
            <button
              onClick={() => setViewType("income")}
              className={`rounded-[1.2rem] px-4 py-3 text-sm font-bold transition ${
                viewType === "income"
                  ? "bg-emerald-600 text-white shadow"
                  : "bg-transparent text-emerald-700"
              }`}
            >
              הכנסות
            </button>

            <button
              onClick={() => setViewType("expense")}
              className={`rounded-[1.2rem] px-4 py-3 text-sm font-bold transition ${
                viewType === "expense"
                  ? "bg-rose-500 text-white shadow"
                  : "bg-transparent text-rose-600"
              }`}
            >
              הוצאות
            </button>
          </div>
        </div>

        <div
          className="rounded-[2rem] bg-white px-4 py-4 shadow-md border border-slate-100"
        >
          <div className="text-center text-lg font-medium tracking-wide text-slate-500">
            {viewType === "expense" ? "סה״כ הוצאות" : "סה״כ הכנסות"}
          </div>

          <div
              className={`mt-1 text-center text-5xl font-bold leading-none ${
                viewType === "expense" ? "text-red-500" : "text-emerald-600"
              }`}
          >
            {formatCurrency(displayedTotal)}
          </div>

          <div className="mt-3 text-center text-sm text-slate-400">
            {selectedMonth ? `${selectedMonth.month}/${selectedMonth.year}` : ""}
          </div>
        </div>

        <div className="rounded-2xl bg-white p-4 shadow-sm">
          <div className="mb-3 text-right text-lg font-semibold">
            {viewType === "expense" ? "חלוקה לקטגוריות" : "חלוקת הכנסות"}
          </div>

          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={chartData}
                  dataKey="amount"
                  nameKey="category"
                  cx="50%"
                  cy="50%"
                  innerRadius={45}
                  outerRadius={88}
                  paddingAngle={3}
                  stroke="#ffffff"
                  strokeWidth={3}
                  labelLine={false}
                  label={renderCustomLabel}
                  onClick={(data) => handlePieClick(data as PieClickData)}
                >
                  {chartData.map((entry, index) => (
                    <Cell
                      key={index}
                      fill={categoryColors[entry.category] || "#94a3b8"}
                      style={{
                        cursor: "pointer",
                        opacity:
                          !selectedCategory || selectedCategory === entry.category
                            ? 1
                            : 0.45,
                      }}
                    />
                  ))}
                </Pie>

                <Tooltip
                  formatter={(value) => formatCurrency(Number(value))}
                  contentStyle={{
                    borderRadius: "12px",
                    border: "1px solid #e2e8f0",
                    boxShadow: "0 4px 14px rgba(0,0,0,0.08)",
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>

          <div className="mt-4 space-y-2">
            {chartData.map((item) => {
              const isSelected = selectedCategory === item.category;

              return (
                <button
                  key={item.category}
                  onClick={() => toggleCategory(item.category)}
                  className={`flex w-full items-center justify-between rounded-xl px-3 py-2 text-right transition ${
                    isSelected
                      ? "bg-emerald-100 ring-1 ring-emerald-300"
                      : "bg-slate-50 hover:bg-slate-100"
                  }`}
                >
                  <span className="text-sm font-semibold text-slate-900">
                    {formatCurrency(item.amount)}
                  </span>

                  <div className="flex items-center gap-2">
                    <span className="text-sm text-slate-700">
                      {item.category}
                    </span>
                    <span
                      className="h-3 w-3 rounded-full"
                      style={{
                        backgroundColor:
                          categoryColors[item.category] || "#94a3b8",
                      }}
                    />
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <button
              onClick={() => setShowCreateModal(true)}
              className="rounded-xl bg-green-600 p-2 text-white shadow-sm hover:bg-green-700"
            >
              <Plus size={18} />
            </button>

            <div className="text-right text-lg font-semibold">רשומות</div>
          </div>

          <div className="flex items-center justify-between">
            <div className="text-sm text-slate-500">
              {selectedCategory
                ? `מסונן לפי: ${selectedCategory}`
                : viewType === "expense"
                ? "כל ההוצאות"
                : "כל ההכנסות"}
            </div>

            {selectedCategory && (
              <button
                onClick={() => setSelectedCategory(null)}
                className="rounded-lg bg-slate-200 px-3 py-1 text-sm text-slate-700 hover:bg-slate-300"
              >
                נקה סינון
              </button>
            )}
          </div>

          {loading ? (
            <div className="rounded-2xl bg-white p-3 text-right text-gray-500 shadow-sm">
              טוען...
            </div>
          ) : filteredTransactions.length === 0 ? (
            <div className="rounded-2xl bg-white p-3 text-right text-gray-500 shadow-sm">
              אין רשומות להצגה
            </div>
          ) : (
            filteredTransactions.map((tx) => (
              <div
                key={tx.id}
                className="flex items-center justify-between rounded-2xl bg-white p-3 shadow-sm"
              >
                <div>
                  <div className="font-semibold">{tx.description}</div>
                  <div className="text-sm text-gray-500">
                    {tx.date} · {tx.category}
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <div className="font-bold">{formatCurrency(tx.amount)}</div>

                  <button
                    onClick={() => openEdit(tx)}
                    className="text-gray-500 hover:text-blue-600"
                  >
                    <Pencil size={18} />
                  </button>

                  <button
                    onClick={() => deleteTransaction(tx.id)}
                    className="text-gray-500 hover:text-red-600"
                  >
                    <Trash2 size={18} />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {showCreateModal && selectedMonth && (
        <div className="fixed inset-0 flex items-center justify-center bg-black/30">
          <div className="w-80 space-y-3 rounded-2xl bg-white p-5 shadow-lg">
            <div className="text-right text-lg font-bold">הוספת רשומה</div>

            <input
              value={newDescription}
              onChange={(e) => setNewDescription(e.target.value)}
              className="w-full rounded-xl border border-slate-300 p-2"
              placeholder="שם"
            />

            <input
              type="number"
              value={newAmount || ""}
              onChange={(e) => setNewAmount(Number(e.target.value))}
              className="w-full rounded-xl border border-slate-300 p-2"
              placeholder="סכום"
            />

            <select
              value={newCategory}
              onChange={(e) => setNewCategory(e.target.value)}
              className="w-full rounded-xl border border-slate-300 p-2"
            >
              {categories.map((c) => (
                <option key={c}>{c}</option>
              ))}
            </select>

            <select
              value={newType}
              onChange={(e) => setNewType(e.target.value)}
              className="w-full rounded-xl border border-slate-300 p-2"
            >
              <option value="expense">הוצאה</option>
              <option value="income">הכנסה</option>
            </select>

            <div className="grid grid-cols-2 gap-2">
              <select
                value={newDay}
                onChange={(e) => setNewDay(Number(e.target.value))}
                className="w-full rounded-xl border border-slate-300 p-2"
              >
                {Array.from(
                  { length: getDaysInMonth(newMonth, selectedMonth.year) },
                  (_, i) => i + 1
                ).map((day) => (
                  <option key={day} value={day}>
                    יום {day}
                  </option>
                ))}
              </select>

              <select
                value={newMonth}
                onChange={(e) => setNewMonth(Number(e.target.value))}
                className="w-full rounded-xl border border-slate-300 p-2"
              >
                {Array.from({ length: 12 }, (_, i) => i + 1).map((month) => (
                  <option key={month} value={month}>
                    חודש {month}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-gray-500"
              >
                <X />
              </button>

              <button onClick={createTransaction} className="text-green-600">
                <Check />
              </button>
            </div>
          </div>
        </div>
      )}

      {editing && selectedMonth && (
        <div className="fixed inset-0 flex items-center justify-center bg-black/30">
          <div className="w-80 space-y-3 rounded-2xl bg-white p-5 shadow-lg">
            <div className="text-right text-lg font-bold">עריכת רשומה</div>

            <input
              value={editDescription}
              onChange={(e) => setEditDescription(e.target.value)}
              className="w-full rounded-xl border border-slate-300 p-2"
              placeholder="שם"
            />

            <input
              type="number"
              value={editAmount}
              onChange={(e) => setEditAmount(Number(e.target.value))}
              className="w-full rounded-xl border border-slate-300 p-2"
              placeholder="סכום"
            />

            <select
              value={editCategory}
              onChange={(e) => setEditCategory(e.target.value)}
              className="w-full rounded-xl border border-slate-300 p-2"
            >
              {categories.map((c) => (
                <option key={c}>{c}</option>
              ))}
            </select>

            <select
              value={editType}
              onChange={(e) => setEditType(e.target.value)}
              className="w-full rounded-xl border border-slate-300 p-2"
            >
              <option value="expense">הוצאה</option>
              <option value="income">הכנסה</option>
            </select>

            <div className="grid grid-cols-2 gap-2">
              <select
                value={editDay}
                onChange={(e) => setEditDay(Number(e.target.value))}
                className="w-full rounded-xl border border-slate-300 p-2"
              >
                {Array.from(
                  { length: getDaysInMonth(editMonth, selectedMonth.year) },
                  (_, i) => i + 1
                ).map((day) => (
                  <option key={day} value={day}>
                    יום {day}
                  </option>
                ))}
              </select>

              <select
                value={editMonth}
                onChange={(e) => setEditMonth(Number(e.target.value))}
                className="w-full rounded-xl border border-slate-300 p-2"
              >
                {Array.from({ length: 12 }, (_, i) => i + 1).map((month) => (
                  <option key={month} value={month}>
                    חודש {month}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={() => setEditing(null)}
                className="text-gray-500"
              >
                <X />
              </button>

              <button onClick={saveEdit} className="text-green-600">
                <Check />
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}