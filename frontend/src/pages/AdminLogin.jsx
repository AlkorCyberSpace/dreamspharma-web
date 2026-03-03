import React, { useState } from "react";
import { Eye, EyeOff, Loader2 } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";

import axios from "axios";
import { loginAPI } from "../services/allAPI";
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

    localStorage.setItem("access", response.data.access);
    localStorage.setItem("refresh", response.data.refresh);

    navigate("/dashboard");

  } catch (error) {
    console.log(error.response?.data);
    setError("Invalid username or password");
  } finally {
    setLoading(false);
  }
};

  return (
    <div
      className="min-h-screen flex items-center"
      style={{
        backgroundImage: "url('/pharma-bg.png')",
        backgroundSize: "cover",
        backgroundPosition: "center",
      }}
    >
      {/* LEFT GLASS BOX */}
      <div
        className="ml-16 w-[400px] px-10 py-8 rounded-3xl 
        backdrop-blur-xl 
        bg-gradient-to-br 
        from-[#2c5e7e]/80 
        via-[#214a67]/80 
        to-[#182f45]/80 
        shadow-2xl 
        border border-white/10"
      >
        <h1 className="text-5xl font-light text-white mb-8">Sign In</h1>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* username */}
          <div>
            <label className="text-sm text-gray-300">username</label>
            <input
              type="text"
              name="username"
              placeholder="test1@gmail.com"
              value={formData.username}
              onChange={handleChange}
              className="w-full mt-2 px-4 py-3 rounded-lg 
              bg-[#123347] 
              text-white 
              placeholder-gray-400 
              focus:outline-none"
            />
          </div>

          {/* Password */}
          <div className="relative">
            <div className="flex justify-between">
              <label className="text-sm text-gray-300">Password</label>
              <span className="text-sm text-gray-300 cursor-pointer">
                Forgot Password ?
              </span>
            </div>

            <input
              type={showPassword ? "text" : "password"}
              name="password"
              placeholder="*************"
              value={formData.password}
              onChange={handleChange}
              className="w-full mt-2 px-4 py-3 rounded-lg 
              bg-[#123347] 
              text-white 
              placeholder-gray-400 
              focus:outline-none"
            />

            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-4 top-[44px] text-gray-400"
            >
              {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
          </div>

          {/* Error Message */}
          {error && (
            <div className="bg-red-500/20 border border-red-500/50 text-red-200 px-4 py-2 rounded-lg text-sm">
              {error}
            </div>
          )}

          {/* Button */}
          <div className="text-center pt-4">
            <button
              type="submit"
              disabled={loading}
              className="px-12 py-3 bg-gray-200 text-black 
              rounded-xl font-medium hover:bg-gray-300 transition
              disabled:opacity-70 disabled:cursor-not-allowed flex items-center justify-center mx-auto min-w-[160px]"
            >
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Signing In...
                </>
              ) : (
                "Sign In"
              )}
            </button>
          </div>

          <p className="text-center text-gray-300 pt-4 text-sm">
            Don’t have an account ?{" "}
            <Link
              to="/signup"
              className="text-white font-medium hover:underline"
            >
              Sign up
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
