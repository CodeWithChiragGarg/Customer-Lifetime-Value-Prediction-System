import "./globals.css";
import Sidebar from "@/components/Sidebar";

export const metadata = {
  title: "CLV Prediction System — Dashboard",
  description:
    "Customer Lifetime Value prediction and segmentation dashboard for data-driven marketing decisions.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-surface">
        {/* Sidebar + Main Content Layout */}
        <div className="flex min-h-screen">
          {/* Dynamic Sidebar Navigation */}
          <Sidebar />

          {/* Main Content */}
          <main className="ml-64 flex-1 p-6 lg:p-8">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
