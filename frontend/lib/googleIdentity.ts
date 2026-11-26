// טעינה של Google Identity Services (כפתור "כניסה עם Google" ו-One Tap).
// https://developers.google.com/identity/gsi/web

export const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || "";

export type GoogleCredentialResponse = {
  credential: string;
};

type GoogleIdApi = {
  initialize: (config: {
    client_id: string;
    callback: (response: GoogleCredentialResponse) => void;
    auto_select?: boolean;
    cancel_on_tap_outside?: boolean;
    use_fedcm_for_prompt?: boolean;
    context?: "signin" | "signup" | "use";
    ux_mode?: "popup" | "redirect";
  }) => void;
  prompt: () => void;
  cancel: () => void;
  disableAutoSelect: () => void;
  renderButton: (
    parent: HTMLElement,
    options: {
      type?: "standard" | "icon";
      theme?: "outline" | "filled_blue" | "filled_black";
      size?: "large" | "medium" | "small";
      text?: "signin_with" | "signup_with" | "continue_with" | "signin";
      shape?: "rectangular" | "pill" | "circle" | "square";
      locale?: string;
      width?: number;
    }
  ) => void;
};

declare global {
  interface Window {
    google?: { accounts: { id: GoogleIdApi } };
  }
}

const SCRIPT_SRC = "https://accounts.google.com/gsi/client";
let loadPromise: Promise<GoogleIdApi> | null = null;

export function loadGoogleIdentity(): Promise<GoogleIdApi> {
  if (typeof window === "undefined") {
    return Promise.reject(new Error("Google Identity is browser-only"));
  }
  if (window.google?.accounts?.id) {
    return Promise.resolve(window.google.accounts.id);
  }
  if (loadPromise) return loadPromise;

  loadPromise = new Promise<GoogleIdApi>((resolve, reject) => {
    const script = document.createElement("script");
    script.src = SCRIPT_SRC;
    script.async = true;
    script.defer = true;
    script.onload = () => {
      if (window.google?.accounts?.id) {
        resolve(window.google.accounts.id);
      } else {
        loadPromise = null;
        reject(new Error("Google Identity failed to initialize"));
      }
    };
    script.onerror = () => {
      loadPromise = null;
      reject(new Error("Failed to load Google Identity script"));
    };
    document.head.appendChild(script);
  });

  return loadPromise;
}

// אחרי התנתקות: שגוגל לא יכניס אוטומטית שוב באותו רגע.
export function disableGoogleAutoSelect() {
  window.google?.accounts?.id?.disableAutoSelect();
}
