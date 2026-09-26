import * as React from "react"
import { cn } from "@/lib/utils"

const Progress = React.forwardRef(({ className, value = 0, ...props }, ref) => (
  <progress ref={ref} className={cn("h-2 w-full", className)} max={100} value={value} {...props} />
))
Progress.displayName = "Progress"

export { Progress }
