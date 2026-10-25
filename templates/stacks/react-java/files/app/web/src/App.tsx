import { useEffect, useState } from "react";

export default function App() {
  const [message, setMessage] = useState("loading...");

  useEffect(() => {
    fetch("/api/hello")
      .then((r) => r.json())
      .then((data) => setMessage(data.message))
      .catch(() => setMessage("the API is not reachable"));
  }, []);

  return (
    <main>
      <h1>@@name@@</h1>
      <p>{message}</p>
    </main>
  );
}
