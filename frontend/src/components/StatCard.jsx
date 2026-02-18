import React from "react";

const gradientVariants = {
  primary:
    "bg-gradient-to-tr from-[#ffffff] via-[#92c0cc] to-[#127690]",

  soft:
    "bg-gradient-to-br from-[#ffffff] via-[#8bbcc9] to-[#127690]",

  strong:
    "bg-[linear-gradient(315deg,#cfe4e9_15%,#92c0cc_50%,#539caf_100%)]",
};


const StatCard = ({ title, value, change, icon: Icon, variant = "primary" }) => {
  return (
    <div
      className={`relative p-4 rounded-xl shadow-md 
      ${gradientVariants[variant]}
      text-gray-800 overflow-hidden`}
    >
      {/* Icon Circle */}
      <div className="absolute right-4 top-6 
                      bg-[#127690] 
                      w-12 h-12 rounded-full 
                      flex items-center justify-center text-white shadow-md">
        <Icon size={22} />
      </div>

      <h2 className="text-3xl font-medium">{value}</h2>
      <p className="mt-2 text-xl font-medium">{title}</p>
      <p className="mt-1 text-sm text-gray-700">{change}</p>
    </div>
  );
};

export default StatCard;
