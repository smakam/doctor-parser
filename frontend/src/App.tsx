import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import LoginPage from "@/pages/LoginPage";
import UploadPage from "@/pages/UploadPage";
import ReviewPage from "@/pages/ReviewPage";
import QuoteFormPage from "@/pages/QuoteFormPage";
import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";
import type { Session } from "@supabase/supabase-js";

function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
      setLoading(false);
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
    });

    // Ensure guest session ID exists for unauthenticated flows
    if (!sessionStorage.getItem("guest_session")) {
      sessionStorage.setItem("guest_session", crypto.randomUUID());
    }

    return () => subscription.unsubscribe();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/upload"
          element={session ? <UploadPage session={session} /> : <UploadPage session={null} />}
        />
        <Route
          path="/review/:id"
          element={<ReviewPage session={session} />}
        />
        <Route
          path="/quote/:id"
          element={<QuoteFormPage />}
        />
        <Route path="/" element={<Navigate to="/upload" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
