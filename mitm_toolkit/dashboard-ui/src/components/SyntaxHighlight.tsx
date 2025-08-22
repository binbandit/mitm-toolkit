import { useEffect, useRef, useState } from 'react'
import Prism from 'prismjs'
import { Copy, Check } from 'lucide-react'
import { Button } from './ui/button'
import 'prismjs/components/prism-json'
import 'prismjs/components/prism-javascript'
import 'prismjs/components/prism-markup'
import 'prismjs/components/prism-css'
import 'prismjs/components/prism-bash'
import 'prismjs/components/prism-yaml'
import 'prismjs/components/prism-typescript'
import 'prismjs/components/prism-python'

// Import a dark theme
import 'prismjs/themes/prism-tomorrow.css'
import '../styles/prism-overrides.css'
import '../styles/code-themes.css'

interface SyntaxHighlightProps {
  code: string
  language?: string
  className?: string
  maxHeight?: string
}

export function SyntaxHighlight({ 
  code, 
  language = 'plaintext',
  className = '',
  maxHeight = '24rem'
}: SyntaxHighlightProps) {
  const codeRef = useRef<HTMLElement>(null)
  const [copied, setCopied] = useState(false)
  const codeTheme = localStorage.getItem('codeTheme') || 'tomorrow'

  useEffect(() => {
    if (codeRef.current) {
      Prism.highlightElement(codeRef.current)
    }
  }, [code, language])

  // Detect language from content if not specified
  const detectLanguage = (content: string): string => {
    if (language !== 'plaintext') return language
    
    const trimmed = content.trim()
    
    // JSON detection
    if ((trimmed.startsWith('{') && trimmed.endsWith('}')) || 
        (trimmed.startsWith('[') && trimmed.endsWith(']'))) {
      try {
        JSON.parse(trimmed)
        return 'json'
      } catch {
        // Not valid JSON, might be JS object
        if (trimmed.includes('=>') || trimmed.includes('function') || trimmed.includes('const')) {
          return 'javascript'
        }
      }
    }
    
    // HTML detection
    if (trimmed.startsWith('<!DOCTYPE') || trimmed.startsWith('<html') || 
        (trimmed.startsWith('<') && trimmed.includes('>'))) {
      return 'markup'
    }
    
    // CSS detection
    if (trimmed.includes('{') && trimmed.includes('}') && 
        (trimmed.includes(':') && trimmed.includes(';'))) {
      if (trimmed.includes('color:') || trimmed.includes('width:') || 
          trimmed.includes('margin:') || trimmed.includes('padding:')) {
        return 'css'
      }
    }
    
    // JavaScript detection
    if (trimmed.includes('function') || trimmed.includes('=>') || 
        trimmed.includes('const ') || trimmed.includes('let ') || 
        trimmed.includes('var ') || trimmed.includes('return ')) {
      return 'javascript'
    }
    
    return 'plaintext'
  }

  const detectedLanguage = detectLanguage(code)
  
  const handleCopy = () => {
    navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  
  return (
    <div className={`relative group overflow-hidden code-theme-${codeTheme} ${className}`} style={{ maxWidth: '100%' }}>
      <div className="absolute top-2 right-2 z-10 flex items-center gap-2">
        <span className="text-[10px] text-muted-foreground bg-background/80 px-1.5 py-0.5 rounded">
          {detectedLanguage}
        </span>
        <Button
          size="icon"
          variant="ghost"
          className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity"
          onClick={handleCopy}
        >
          {copied ? (
            <Check className="h-3 w-3 text-green-500" />
          ) : (
            <Copy className="h-3 w-3" />
          )}
        </Button>
      </div>
      <pre 
        className="!bg-[#2d2d2d] !text-[#cccccc] p-2 rounded-md overflow-auto !text-[11px] !leading-relaxed" 
        style={{ maxHeight, margin: 0, width: '100%', maxWidth: '100%' }}
      >
        <code 
          ref={codeRef}
          className={`language-${detectedLanguage} block`}
          style={{ 
            fontSize: 'inherit', 
            lineHeight: 'inherit',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
            overflowWrap: 'break-word'
          }}
        >
          {code}
        </code>
      </pre>
    </div>
  )
}