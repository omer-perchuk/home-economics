"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

export default function AuthPageClient() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const hasRunRef = useRef(false);

  const [message, setMessage] = useState("מאמת כניסה...");
  const [error, setError] = useState("");

  useEffect(() => {
    if (hasRunRef.current) return;
    hasRunRef.current = true;

    const token = searchParams.get("token");

    if (!token) {
      setError("הגישה לאתר אפשרית רק דרך קישור מהבוט.");
      return;
    }

    fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/auth/verify-magic-link`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ token }),
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

        // 🔥 שומרים token
        localStorage.setItem("access_token", data.access_token);

        setMessage("הכניסה הצליחה, מעביר...");

        setTimeout(() => {
          router.replace("/");
        }, 800);
      })
      .catch((err) => {
        console.error("verify-magic-link failed:", err);
        setError("הקישור לא תקין או שפג תוקפו.");
      });
  }, [router, searchParams]);

  return (
    <main style={{ padding: "40px", fontFamily: "sans-serif" }}>
      {error ? <h2>{error}</h2> : <h2>{message}</h2>}
    </main>
  );
}