import React, { useState } from "react";
import { Eye, EyeOff } from "lucide-react";
import { Link } from "react-router-dom";

export default function AdminSignup() {
  const [showPassword, setShowPassword] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    password: "",
  });

  const handleChange = (e) => {
    setFormData((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    console.log(formData);
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
        className="ml-16 w-[380px] px-8 py-6 rounded-3xl 
        backdrop-blur-xl 
        bg-gradient-to-br 
        from-[#2c5e7e]/80 
        via-[#214a67]/80 
        to-[#182f45]/80 
        shadow-2xl 
        border border-white/10"
      >
        <h1 className="text-4xl font-light text-white mb-6">Sign Up</h1>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Name */}
          <div>
            <label className="text-sm text-gray-300">Full Name</label>
            <input
              type="text"
              name="name"
              placeholder="Enter your name"
              value={formData.name}
              onChange={handleChange}
              className="w-full mt-2 px-4 py-2 rounded-lg 
              bg-[#123347] 
              text-white 
              placeholder-gray-400 
              focus:outline-none"
            />
          </div>

          {/* Email */}
          <div>
            <label className="text-sm text-gray-300">Email</label>
            <input
              type="email"
              name="email"
              placeholder="test1@gmail.com"
              value={formData.email}
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
            <label className="text-sm text-gray-300">Password</label>

            <input
              type={showPassword ? "text" : "password"}
              name="password"
              placeholder="Create password"
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

          {/* Button */}
          <div className="text-center pt-4">
            <button
              type="submit"
              className="px-12 py-3 bg-gray-200 text-black 
              rounded-xl font-medium hover:bg-gray-300 transition"
            >
              Sign Up
            </button>
          </div>

          <p className="text-center text-gray-300 pt-4 text-sm">
            Already have an account ?{" "}
            <Link
              to="/login"
              className="text-white font-medium hover:underline"
            >
              Sign in
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
