import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import DashboardLayout from "./pages/DashboardLayout";
import Dashboard from "./components/Dashboard";
import AdminLogin from "./pages/AdminLogin";
import AdminSignup from "./pages/AdminSignup";
import Orders from "./components/Orders";

import Retailers from "./pages/Retailers";
import Refunds from "./pages/Refunds";
import Reports from "./pages/Reports";
import Products from "./pages/Products";
import Profile from "./pages/Profile";
import OffersAndBanners from "./pages/OffersAndBanners";
import AuditLogs from "./pages/AuditLogs";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Redirect root to login */}
        <Route path="/" element={<Navigate to="/login" replace />} />

        {/* Standalone login page */}
        <Route path="/login" element={<AdminLogin />} />

        {/* Standalone signup page */}
        <Route path="/signup" element={<AdminSignup />} />

        {/* Dashboard layout with nested routes */}
        <Route path="/" element={<DashboardLayout />}>
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="orders" element={<Orders />} />
          <Route path="refunds" element={<Refunds />} />
          <Route path="retailers" element={<Retailers />} />
          <Route path="products" element={<Products />} />
          <Route path="reports" element={<Reports />} />
          <Route path="Profile" element={<Profile />} />
          <Route path="offers" element={<OffersAndBanners />} />
          <Route path="audit" element={<AuditLogs />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
