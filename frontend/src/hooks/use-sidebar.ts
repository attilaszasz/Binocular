import { useCallback, useEffect, useState } from "react"

const STORAGE_KEY = "binocular-sidebar-collapsed"
const MOBILE_BREAKPOINT = 768

export function useSidebar() {
  const [collapsed, setCollapsedState] = useState<boolean>(() => {
    if (typeof window === "undefined") return false
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored !== null) return stored === "true"
    return window.innerWidth <= MOBILE_BREAKPOINT
  })

  const setCollapsed = useCallback((value: boolean) => {
    setCollapsedState(value)
    localStorage.setItem(STORAGE_KEY, String(value))
  }, [])

  const toggle = useCallback(() => {
    setCollapsed(!collapsed)
  }, [collapsed, setCollapsed])

  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth <= MOBILE_BREAKPOINT) {
        setCollapsedState(true)
      }
    }

    window.addEventListener("resize", handleResize)
    return () => window.removeEventListener("resize", handleResize)
  }, [])

  return { collapsed, setCollapsed, toggle }
}
