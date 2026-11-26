"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { LogOut } from "lucide-react";

import {
  GOOGLE_CLIENT_ID,
  GoogleCredentialResponse,
  disableGoogleAutoSelect,
  loadGoogleIdentity,
} from "@/lib/googleIdentity";

const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Me = {
  google_linked?: boolean;
  google_email?: string | null;
};

function authHeaders(): Record<string, string> {
  const token = localStorage.getItem("access_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// חלק בתפריט: חיבור חשבון גוגל והתנתקות.
export default function AccountMenuSection() {
  const router = useRouter();
  const buttonRef = useRef<HTMLDivElement>(null);
  const [me, setMe] = useState<Me | null>(null);
  const [status, setStatus] = useState("");

  const loadMe = useCallback(async () => {
    try {
      const res = await fetch(`${backendUrl}/api/me`, { headers: authHeaders() });
      if (res.ok) setMe(await res.json());
    } catch (err) {
      console.error("load /api/me failed:", err);
    }
  }, []);

  useEffect(() => {
    loadMe();
  }, [loadMe]);

  const handleLinkCredential = useCallback(
    async (response: GoogleCredentialResponse) => {
      setStatus("");
      try {
        const res = await fetch(`${backendUrl}/api/auth/google/link`, {
          method: "POST",
          headers: { "Content-Type": "application/json", ...authHeaders() },
          body: JSON.stringify({ credential: response.credential }),
        });

        if (res.status === 409) {
          setStatus("חשבון הגוגל הזה כבר מחובר למשתמש אחר.");
          return;
        }
        if (!res.ok) throw new Error(await res.text());

        setStatus("חשבון הגוגל חובר. מעכשיו אפשר להיכנס איתו.");
        loadMe();
      } catch (err) {
        console.error("link google failed:", err);
        setStatus("החיבור לגוגל נכשל. נסה שוב.");
      }
    },
    [loadMe]
  );

  // כפתור "המשך עם Google" לחיבור החשבון, רק כשעוד לא חובר.
  useEffect(() => {
    if (!me || me.google_linked || !GOOGLE_CLIENT_ID) return;

    loadGoogleIdentity()
      .then((googleId) => {
        googleId.initialize({
          client_id: GOOGLE_CLIENT_ID,
          callback: handleLinkCredential,
          auto_select: false,
          context: "use",
        });
        if (buttonRef.current) {
          buttonRef.current.innerHTML = "";
          googleId.renderButton(buttonRef.current, {
            theme: "outline",
            size: "medium",
            text: "continue_with",
            shape: "pill",
            locale: "he",
            width: 210,
          });
        }
      })
      .catch((err) => console.error(err));
  }, [me, handleLinkCredential]);

  async function unlinkGoogle() {
    try {
      await fetch(`${backendUrl}/api/auth/google/link`, {
        method: "DELETE",
        headers: authHeaders(),
      });
      disableGoogleAutoSelect();
      setStatus("חשבון הגוגל נותק.");
      loadMe();
    } catch (err) {
      console.error("unlink google failed:", err);
    }
  }

  async function logout() {
    try {
      await fetch(`${backendUrl}/api/auth/logout`, {
        method: "POST",
        headers: authHeaders(),
      });
    } catch (err) {
      console.error("logout failed:", err);
    }
    localStorage.removeItem("access_token");
    disableGoogleAutoSelect();
    router.replace("/auth?logged_out=1");
  }

  return (
    <div className="space-y-3 border-t border-slate-200 pt-4">
      {GOOGLE_CLIENT_ID && me ? (
        me.google_linked ? (
          <div className="space-y-1 text-sm text-slate-600">
            <div>מחובר עם Google</div>
            {me.google_email ? (
              <div className="truncate text-xs text-slate-500" dir="ltr">
                {me.google_email}
              </div>
            ) : null}
            <button
              onClick={unlinkGoogle}
              className="text-xs text-slate-400 underline hover:text-red-600"
            >
              נתק חשבון גוגל
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            <div className="text-sm font-medium text-slate-700">חבר חשבון גוגל</div>
            <div className="text-xs text-slate-500">
              כדי להיכנס בפעם הבאה בלחיצה אחת, בלי קישור מהבוט.
            </div>
            <div ref={buttonRef} />
          </div>
        )
      ) : null}

      {status ? <div className="text-xs text-green-700">{status}</div> : null}

      <button
        onClick={logout}
        className="flex items-center gap-2 text-lg text-slate-700 hover:text-red-600"
      >
        <LogOut size={20} />
        התנתק
      </button>
    </div>
  );
}
