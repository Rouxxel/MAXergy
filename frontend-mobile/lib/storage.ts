import AsyncStorage from "@react-native-async-storage/async-storage";
import { type PersistStorage } from "zustand/middleware";

export const zustandStorage: PersistStorage<any> = {
  setItem: async (name, value) => {
    await AsyncStorage.setItem(name, JSON.stringify(value));
  },
  getItem: async (name) => {
    const value = await AsyncStorage.getItem(name);
    return value ? JSON.parse(value) : null;
  },
  removeItem: async (name) => {
    await AsyncStorage.removeItem(name);
  },
};
