import { createContext, useContext, useEffect, useState, ReactNode } from 'react'

type Theme = 'dark' | 'light'
type CodeTheme = 'tomorrow' | 'dracula' | 'github' | 'monokai' | 'nord' | 'one-dark'

interface ThemeContextType {
  theme: Theme
  codeTheme: CodeTheme
  setTheme: (theme: Theme) => void
  setCodeTheme: (theme: CodeTheme) => void
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined)

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(() => {
    const saved = localStorage.getItem('theme')
    return (saved as Theme) || 'dark'
  })
  
  const [codeTheme, setCodeThemeState] = useState<CodeTheme>(() => {
    const saved = localStorage.getItem('codeTheme')
    return (saved as CodeTheme) || 'tomorrow'
  })

  useEffect(() => {
    const root = document.documentElement
    root.classList.remove('light', 'dark')
    root.classList.add(theme)
    localStorage.setItem('theme', theme)
  }, [theme])

  useEffect(() => {
    localStorage.setItem('codeTheme', codeTheme)
  }, [codeTheme])

  const setTheme = (newTheme: Theme) => {
    setThemeState(newTheme)
  }

  const setCodeTheme = (newTheme: CodeTheme) => {
    setCodeThemeState(newTheme)
  }

  return (
    <ThemeContext.Provider value={{ theme, codeTheme, setTheme, setCodeTheme }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const context = useContext(ThemeContext)
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }
  return context
}