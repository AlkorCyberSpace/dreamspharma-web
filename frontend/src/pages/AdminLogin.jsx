import React, { useState } from "react";
import { Eye, EyeOff } from "lucide-react";

export default function AdminLogin() {
    const [showPassword, setShowPassword] = useState(false);
    const [formData, setFormData] = useState({ email: "", password: "" });

    const handleChange = (e) => {
        setFormData((prev) => ({ ...prev, [e.target.name]: e.target.value }));
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        // TODO: wire up authentication
        console.log("Login attempt:", formData);
    };

    return (
        <div className="flex items-center justify-center h-screen bg-[#1b1835]">
            <div className="bg-white p-1 mx-3 rounded-lg shadow-md w-full max-w-full d-flex flex-row lg-flex-col gap-5">
              <div className="col">
                

              </div>
              <div className="col">
       
                
              </div>
            </div>

        </div>
    );
}

