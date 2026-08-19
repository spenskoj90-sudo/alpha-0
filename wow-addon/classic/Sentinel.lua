local frame = CreateFrame("Frame", "SentinelClassicOverlay", UIParent)
frame:SetSize(330, 150)
frame:SetPoint("TOPRIGHT", UIParent, "TOPRIGHT", -24, -90)
frame:SetBackdrop({bgFile = "Interface\\DialogFrame\\UI-DialogBox-Background", edgeFile = "Interface\\Tooltips\\UI-Tooltip-Border", edgeSize = 12, insets = {left=4,right=4,top=4,bottom=4}})
frame:SetBackdropColor(0.025, 0.04, 0.055, 0.88)
frame:SetBackdropBorderColor(0.22, 0.62, 0.76, 0.85)
frame:SetMovable(true)
frame:EnableMouse(true)
frame:RegisterForDrag("LeftButton")
frame:SetScript("OnDragStart", frame.StartMoving)
frame:SetScript("OnDragStop", frame.StopMovingOrSizing)

local title = frame:CreateFontString(nil, "OVERLAY", "GameFontNormal")
title:SetPoint("TOPLEFT", 14, -12)
title:SetText("SENTINEL  /  PROTECTION ACTIVE")
title:SetTextColor(0.60, 0.85, 0.35)

local info = frame:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
info:SetPoint("TOPLEFT", 14, -36)
info:SetJustifyH("LEFT")
info:SetTextColor(0.82, 0.88, 0.92)

local security = frame:CreateFontString(nil, "OVERLAY", "GameFontNormal")
security:SetPoint("TOPRIGHT", -14, -12)
security:SetText("● SECURE")
security:SetTextColor(0.20, 0.90, 0.35)

local paused = false
local locked = false
local function refresh()
    local name, realm = UnitName("player")
    local ping = 0
    if GetNetStats then
        local _, _, home, world = GetNetStats()
        ping = tonumber(world or home or 0) or 0
    end
    info:SetText(string.format("REALM  %s\nPING   %d ms\nPATCH  CLASSIC COMPATIBILITY PROFILE\nMODE   PASSIVE TELEMETRY", realm or GetRealmName() or "Unknown", ping))
    if locked then
        title:SetText("SENTINEL  /  SESSION LOCKED")
        title:SetTextColor(0.95, 0.20, 0.25)
        security:SetText("● LOCKED")
        security:SetTextColor(0.95, 0.20, 0.25)
    elseif paused then
        title:SetText("SENTINEL  /  PROTECTION PAUSED")
        title:SetTextColor(0.95, 0.72, 0.18)
        security:SetText("● ATTENTION")
        security:SetTextColor(0.95, 0.72, 0.18)
    elseif ping > 180 then
        security:SetText("● ATTENTION")
        security:SetTextColor(0.95, 0.72, 0.18)
    else
        title:SetText("SENTINEL  /  PROTECTION ACTIVE")
        title:SetTextColor(0.60, 0.85, 0.35)
        security:SetText("● SECURE")
        security:SetTextColor(0.20, 0.90, 0.35)
    end
end

local function button(text, x, fn, width)
    local b = CreateFrame("Button", nil, frame, "UIPanelButtonTemplate")
    b:SetSize(width, 24)
    b:SetPoint("BOTTOMLEFT", x, 10)
    b:SetText(text)
    b:SetScript("OnClick", fn)
    return b
end

button("PAUSE", 12, function() if not locked then paused = not paused; refresh() end end, 60)
button("SETTINGS", 78, function() print("SENTINEL: configuration is managed by the control plane.") end, 72)
button("SCREENSHOT", 156, function() Screenshot() end, 88)
button("LOCK", 250, function() locked = true; paused = true; refresh() end, 54)

frame:SetScript("OnUpdate", function(self, elapsed)
    self._elapsed = (self._elapsed or 0) + elapsed
    if self._elapsed >= 2 then self._elapsed = 0; refresh() end
end)

SLASH_SENTINEL1 = "/sentinel"
SlashCmdList.SENTINEL = function(msg)
    msg = (msg or ""):lower()
    if msg == "hide" then frame:Hide() elseif msg == "show" then frame:Show() elseif msg == "lock" then locked=true; paused=true; refresh() else print("SENTINEL commands: /sentinel show | hide | lock") end
end

refresh()
