"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"

export default function Home() {
  const router = useRouter()

  useEffect(() => {
    const setupComplete = localStorage.getItem("aegis_setup_complete")
    if (setupComplete === "true") {
      router.replace("/logs")
    } else {
      router.replace("/setup")
    }
  }, [router])

  // Show nothing while determining redirect
  return null
}
