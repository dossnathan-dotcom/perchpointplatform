import * as React from "react"
import { X } from "lucide-react"
import { cn } from "@/lib/utils"

const DialogContext = React.createContext(null)

function Dialog({ open = false, onOpenChange, children }) {
  return <DialogContext.Provider value={{ open, onOpenChange }}>{children}</DialogContext.Provider>
}

const DialogTrigger = ({ children }) => children
const DialogPortal = ({ children }) => children
const DialogClose = ({ children, ...props }) => {
  const dialog = React.useContext(DialogContext)
  return <button type="button" {...props} onClick={() => dialog?.onOpenChange?.(false)}>{children}</button>
}
const DialogOverlay = React.forwardRef(({ className, ...props }, ref) => (
  <div ref={ref} className={cn("fixed inset-0 z-50 bg-black/80", className)} {...props} />
))
DialogOverlay.displayName = "DialogOverlay"

const DialogContent = React.forwardRef(({ className, children, ...props }, ref) => {
  const dialog = React.useContext(DialogContext)
  const localRef = React.useRef(null)
  const onOpenChange = React.useRef(dialog?.onOpenChange)
  onOpenChange.current = dialog?.onOpenChange
  React.useEffect(() => {
    if (!dialog?.open) return undefined
    const previous = document.activeElement
    localRef.current?.focus()
    const onKey = (event) => {
      if (event.key === "Escape") onOpenChange.current?.(false)
    }
    document.addEventListener("keydown", onKey)
    return () => {
      document.removeEventListener("keydown", onKey)
      if (previous instanceof HTMLElement) previous.focus()
    }
  }, [dialog?.open])
  if (!dialog?.open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4">
      <div
        ref={(node) => {
          localRef.current = node
          if (typeof ref === "function") ref(node)
          else if (ref) ref.current = node
        }}
        role="dialog"
        aria-modal="true"
        tabIndex={-1}
        className={cn("relative grid max-h-[90vh] w-[min(32rem,calc(100vw-2rem))] gap-4 overflow-y-auto border bg-background p-6", className)}
        {...props}>
        {children}
        <button type="button" aria-label="Close" data-testid={props["data-testid"] ? `${props["data-testid"]}-close` : undefined} className="absolute right-2 top-2 flex h-11 w-11 items-center justify-center" onClick={() => dialog.onOpenChange?.(false)}>
          <X className="h-4 w-4" />
          <span className="sr-only">Close</span>
        </button>
      </div>
    </div>
  )
})
DialogContent.displayName = "DialogContent"

const DialogHeader = ({ className, ...props }) => <div className={cn("flex flex-col gap-2 text-left", className)} {...props} />
DialogHeader.displayName = "DialogHeader"
const DialogFooter = ({ className, ...props }) => <div className={cn("flex flex-col-reverse gap-2 sm:flex-row sm:justify-end", className)} {...props} />
DialogFooter.displayName = "DialogFooter"
const DialogTitle = React.forwardRef(({ className, ...props }, ref) => <h2 ref={ref} className={cn("text-lg font-semibold", className)} {...props} />)
DialogTitle.displayName = "DialogTitle"
const DialogDescription = React.forwardRef(({ className, ...props }, ref) => <p ref={ref} className={cn("text-sm", className)} {...props} />)
DialogDescription.displayName = "DialogDescription"

export { Dialog, DialogPortal, DialogOverlay, DialogTrigger, DialogClose, DialogContent, DialogHeader, DialogFooter, DialogTitle, DialogDescription }
