import { Toaster } from "sonner";
import Dashboard from "./components/Dashboard";

export default function App() {
  return (
    <>
      <Dashboard />
      <Toaster position="top-right" theme="dark" richColors closeButton />
    </>
  );
}
