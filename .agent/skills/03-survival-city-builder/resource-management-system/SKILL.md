---
name: resource-management-system
description: "Economy system for tracking integer-based resources (Gold, Wood, Food) with ScriptableObject keys and event-driven updates."
version: 1.0.0
argument-hint: "action='Add' resource='Gold' amount=100"
disable-model-invocation: false
user-invocable: true
allowed-tools:
  - run_command
  - list_dir
  - write_to_file
---

# Resource Management System

## Overview
A data-driven economy system where Resources are defined as `ScriptableObjects`. The Manager holds the inventory (`Dictionary<Resource, int>`) and broadcasts events when values change for UI updates.

## When to Use
- Use for RTS/City Builders (Wood, Stone, Gold)
- Use for RPG Currencies (Gem, Coin, Karma)
- Use for Crafting Ingredients
- Use for tracking ammo or fuel
- Use for validating building costs

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ECONOMY SYSTEM                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  RESOURCE DATA (Type)     RESOURCE MANAGER (Inventory)      │
│  ┌────────────────┐      ┌───────────────────────────┐      │
│  │ "Gold.asset"   │──────▶ Dictionary<Type, int>     │      │
│  │ "Wood.asset"   │      │ [Gold: 100]               │      │
│  └────────────────┘      │ [Wood: 50]                │      │
│                          └─────────────┬─────────────┘      │
│                                        │                    │
│                                        ▼                    │
│    UI DISPLAY               ┌───────────────────────────┐   │
│  ┌────────────────┐         │ EVENT: OnResourceChanged  │   │
│  │ Update Text()  │◀────────│ (Type, NewValue)          │   │
│  └────────────────┘         └───────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Best Practices
- ✅ Use `ScriptableObjects` as Keys (prevents string errors like "gold" vs "Gold").
- ✅ Use generic interfaces like `ICost` that accepts `ResourceAmount` structs.
- ✅ Implement `CanAfford()` and `Spend()` helper methods.
- ✅ Separate the UI from the Data (Observer pattern).
- ❌ **NEVER** use Strings as keys (`dict["Gold"]`).
- ❌ **NEVER** update UI in `Update()`; use Events.

## Few-Shot Examples

### Example 1: Defining Resource
**User**: "Create a Wood resource."

**Agent**:
```csharp
[CreateAssetMenu(menuName = "Economy/Resource")]
public class ResourceType : ScriptableObject
{
    public string DisplayName;
    public Sprite Icon;
}
```

### Example 2: Transaction
**User**: "Add 100 wood."

**Agent**:
```csharp
public void AddResource(ResourceType type, int amount)
{
    if (!_inventory.ContainsKey(type)) _inventory[type] = 0;
    
    _inventory[type] += amount;
    OnResourceChanged?.Invoke(type, _inventory[type]);
}
```

## Related Skills
- `@event-bus-system` - Event System
- `@ui-toolkit-modern` - Resource Bar UI
