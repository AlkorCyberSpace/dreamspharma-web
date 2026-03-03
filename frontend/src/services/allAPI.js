import axios from "axios";


export const loginAPI = async (loginData) => {
  try {
    const response = await axios.post(
      `${serverUrl}auth/login/`,
      loginData
    );
    return response;
  } catch (error) {
    throw error;
  }

};
