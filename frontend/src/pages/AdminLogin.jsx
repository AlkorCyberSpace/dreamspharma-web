import React, { useState } from "react";
import { Eye, EyeOff, Loader2 } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";

import axios from "axios";
import { loginAPI } from "../services/allAPI";
import loginBg from "../assets/login-page.png";
import logoImg from "../assets/DP-logo.png";

export default function AdminLogin() {
  const [showPassword, setShowPassword] = useState(false);
  const [formData, setFormData] = useState({ username: "", password: "" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const handleChange = (e) => {
    setError("");
    setFormData((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  };


  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const response = await loginAPI({
        username: formData.username,
        password: formData.password,
      });

      const { access, refresh } = response.data;

      localStorage.setItem("access", access);
      localStorage.setItem("refresh", refresh);
      navigate("/dashboard");
    } catch (error) {
      console.log(error);
      setError("Invalid username or password");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="min-h-screen flex items-center justify-center relative overflow-hidden font-outfit"
      style={{
        backgroundImage: `url(${loginBg})`,
        backgroundSize: "cover",
        backgroundPosition: "center",
        backgroundRepeat: "no-repeat"
      }}
    >
      {/* Subtle overlay for better readability */}

      <div className="container mx-auto px-6 lg:px-24 flex flex-col lg:flex-row items-center justify-between relative z-10 w-full gap-12">

        {/* Left Side: Logo Branding */}
        <div className="hidden lg:flex flex-col items-center justify-center flex-1 max-w-lg">
          <img
            src={logoImg}
            alt="Dreams Pharma"
            className="w-full h-auto "
          />
        </div>

        {/* Right Side: Glassmorphism Login Card */}
        <div
          className="w-full max-w-[480px] p-10 lg:py-22
          backdrop-blur-lg
          shadow-[0_10px_10px_-15px_rgba(0,0,0,0.1)]
          border border-white/10"
        >
          <div className="mb-9 text-center">
            <h1 className="text-5xl font-medium text-[#133D69] tracking-tight opacity-90">Sign In</h1>
          </div>

          <form onSubmit={handleSubmit} className="space-y-3">
            <div className="space-y-2">
              <label className="text-sm font-medium text-[#133D69] ml-1">Email</label>
              <input
                type="text"
                name="username"
                placeholder="test1@gmail.com"
                value={formData.username}
                onChange={handleChange}
                className="w-full px-6 py-3 rounded-2xl 
                bg-white/10 
                text-[#1e3a8a] 
                placeholder-[#1e3a8a]/30 
                border border-white/50
                focus:outline-none focus:bg-white/20 transition-all shadow-sm"
                required
              />
            </div>

            <div className="relative space-y-2">
              <div className="flex justify-between items-center px-1">
                <label className="text-sm font-medium text-[#133D69]">Password</label>
                <span className="text-xs font-medium text-[#133D69] cursor-pointer hover:text-blue-600 transition-colors">
                  Forgot Password ?
                </span>
              </div>

              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  name="password"
                  placeholder="*************"
                  value={formData.password}
                  onChange={handleChange}
                  className="w-full px-6 py-3 rounded-2xl 
                  bg-white/10 
                  text-[#1e3a8a] 
                  placeholder-[#1e3a8a]/30 
                  border border-white/50
                  focus:outline-none focus:ring-2 focus:ring-blue-400/30 transition-all shadow-sm"
                  required
                />

                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-5 top-1/2 -translate-y-1/2 text-[#1e3a8a]/50 hover:text-[#1e3a8a] transition-colors"
                >
                  {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                </button>
              </div>
            </div>

            {error && (
              <div className="bg-red-500/10 border border-red-500/20 text-red-700 px-4 py-3 rounded-xl text-sm font-medium animate-shake">
                {error}
              </div>
            )}

            <div className="pt-4 flex justify-center">
              <button
                type="submit"
                disabled={loading}
                className="w-[230px] py-2 bg-[#133D69] text-white 
                rounded-xl font-semibold text-base hover:bg-[#102b52] transition-all
                disabled:opacity-70 disabled:cursor-not-allowed flex items-center justify-center shadow-lg active:scale-[0.98]"
              >
                {loading ? (
                  <>
                    <Loader2 className="mr-3 h-5 w-5 animate-spin" />
                    Authenticating...
                  </>
                ) : (
                  "Sign In"
                )}
              </button>
            </div>


          </form>
        </div>
      </div>
    </div>
  );
}
