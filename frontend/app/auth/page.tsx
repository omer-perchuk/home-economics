import { Suspense } from "react";
import AuthPageClient from "./AuthPageClient";

export default function AuthPage() {
  return (
    <Suspense fallback={<main style={{ padding: "40px", fontFamily: "sans-serif" }}><h2>מאמת כניסה...</h2></main>}>
      <AuthPageClient />
    </Suspense>
  );
}