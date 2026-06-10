import { Monitor } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export function InventoryPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold tracking-tight">Inventory</h1>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Monitor className="h-5 w-5" />
            Device Inventory
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">
            Device inventory will be available here once the inventory module is
            implemented.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
