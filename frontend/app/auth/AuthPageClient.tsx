"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import {
  GOOGLE_CLIENT_ID,
  GoogleCredentialResponse,
  loadGoogleIdentity,
} from "@/lib/googleIdentity";

const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Mode = "verifying" | "login" | "success" | "error";

export default function AuthPageClient() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const hasRunRef = useRef(false);
  const googleButtonRef = useRef<HTMLDivElement>(null);

  const [mode, setMode] = useState<Mode>("verifying");
  const [message, setMessage] = useState("מאמת כניסה...");
  const [error, setError] = useState("");

  const loggedOut = searchParams.get("logged_out") === "1";
  const redirectParam = searchParams.get("redirect");
  const redirectTarget =
    redirectParam && redirectParam.startsWith("/") ? redirectParam : "/";

  const finishLogin = useCallback(
    (accessToken: string) => {
      localStorage.setItem("access_token", accessToken);
      setMode("success");
      setMessage("הכניסה הצליחה, מעביר...");
      setTimeout(() => {
        router.replace(redirectTarget);
      }, 600);
    },
    [router, redirectTarget]
  );

  const handleGoogleCredential = useCallback(
    async (response: GoogleCredentialResponse) => {
      setError("");
      try {
        const res = await fetch(`${backendUrl}/api/auth/google`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ credential: response.credential }),
        });

        if (res.status === 403) {
          setError(
            "חשבון הגוגל הזה עוד לא מחובר למשתמש. שלח הודעה לבוט בוואטסאפ, היכנס דרך הקישור שתקבל, ובתפריט לחץ \"חבר חשבון גוגל\"."
          );
          return;
        }

        if (!res.ok) {
          throw new Error(await res.text());
        }

        const data = await res.json();
        if (!data.access_token) throw new Error("missing access token");
        finishLogin(data.access_token);
      } catch (err) {
        console.error("google login failed:", err);
        setError("הכניסה עם גוגל נכשלה. נסה שוב.");
      }
    },
    [finishLogin]
  );

  // שלב 1: קישור מהבוט / כניסת חירום, או בדיקה אם כבר מחוברים.
  useEffect(() => {
    if (hasRunRef.current) return;
    hasRunRef.current = true;

    const token = searchParams.get("token");
    const masterKey = searchParams.get("master");

    if (!token && !masterKey) {
      const existing = localStorage.getItem("access_token");
      if (!existing) {
        setMode("login");
        return;
      }

      fetch(`${backendUrl}/api/me`, {
        headers: { Authorization: `Bearer ${existing}` },
      })
        .then((res) => {
          if (res.ok) {
            router.replace(redirectTarget);
          } else {
            localStorage.removeItem("access_token");
            setMode("login");
          }
        })
        .catch(() => setMode("login"));
      return;
    }

    const endpoint = token
      ? "/api/auth/verify-magic-link"
      : "/api/auth/master-login";
    const body = token ? { token } : {};

    fetch(`${backendUrl}${endpoint}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    })
      .then(async (res) => {
        if (!res.ok) {
          const text = await res.text();
          throw new Error(text || "invalid");
        }
        return res.json();
      })
      .then((data) => {
        if (!data.access_token) {
          throw new Error("missing access token");
        }
        finishLogin(data.access_token);
      })
      .catch((err) => {
        console.error("verify-magic-link failed:", err);
        setMode("login");
        setError("הקישור לא תקין או שפג תוקפו.");
      });
  }, [router, searchParams, redirectTarget, finishLogin]);

  // שלב 2: דף כניסה עם גוגל (One Tap + כפתור).
  useEffect(() => {
    if (mode !== "login" || !GOOGLE_CLIENT_ID) return;

    let cancelled = false;

    loadGoogleIdentity()
      .then((googleId) => {
        if (cancelled) return;

        googleId.initialize({
          client_id: GOOGLE_CLIENT_ID,
          callback: handleGoogleCredential,
          auto_select: true,
          cancel_on_tap_outside: false,
          use_fedcm_for_prompt: true,
          context: "signin",
        });

        if (googleButtonRef.current) {
          googleButtonRef.current.innerHTML = "";
          googleId.renderButton(googleButtonRef.current, {
            theme: "outline",
            size: "large",
            text: "signin_with",
            shape: "pill",
            locale: "he",
            width: 280,
          });
        }

        // אחרי התנתקות לא מקפיצים את חלון One Tap, רק מציגים את הכפתור.
        if (!loggedOut) googleId.prompt();
      })
      .catch((err) => {
        console.error(err);
        setError("לא הצלחנו לטעון את הכניסה עם גוגל.");
      });

    return () => {
      cancelled = true;
      window.google?.accounts?.id?.cancel();
    };
  }, [mode, handleGoogleCredential, loggedOut]);

  if (mode === "verifying" || mode === "success") {
    return (
      <main style={{ padding: "40px", fontFamily: "sans-serif" }}>
        <h2>{message}</h2>
      </main>
    );
  }

  return (
    <main
      dir="rtl"
      className="flex min-h-screen items-center justify-center bg-gradient-to-b from-green-50 via-emerald-50 to-lime-50 p-4 text-slate-900"
    >
      <div className="w-full max-w-sm space-y-5 rounded-3xl bg-white p-6 text-center shadow-lg">
        <h1 className="text-2xl font-bold text-green-700">כלכלת הבית</h1>

        {GOOGLE_CLIENT_ID ? (
          <>
            <p className="text-slate-600">התחבר עם חשבון הגוגל שלך</p>
            <div className="flex justify-center" ref={googleButtonRef} />
          </>
        ) : null}

        {error ? (
          <p className="rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</p>
        ) : null}

        <p className="text-sm text-slate-500">
          פעם ראשונה? שלח הודעה לבוט בוואטסאפ ותקבל קישור כניסה.
        </p>
      </div>
    </main>
  );
}
