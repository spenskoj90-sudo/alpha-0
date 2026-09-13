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
local snapshotReady = false
local snapshotSequence = 0

local function clamp(v, lo, hi)
    if v < lo then return lo end
    if v > hi then return hi end
    return v
end

local function patchProfile()
    local _, _, _, interfaceVersion = GetBuildInfo()
    local interface = tonumber(interfaceVersion or 0) or 0
    if interface >= 30300 and interface < 40000 then return "wotlk-3.3.5a" end
    if interface >= 20400 and interface < 30000 then return "tbc-2.4.3" end
    return "vanilla-1.12"
end

local function combatState()
    if UnitAffectingCombat then return UnitAffectingCombat("player") and "COMBAT" or "IDLE" end
    return "UNKNOWN"
end

local function writeCheckpoint(realm, ping)
    if not snapshotReady then return end
    SentinelDB = SentinelDB or {}
    snapshotSequence = snapshotSequence + 1
    SentinelDB.snapshot_sequence = snapshotSequence
    SentinelDB.snapshot = {
        schema_version = 1,
        sequence = snapshotSequence,
        observed_at_epoch = time(),
        patch_profile = patchProfile(),
        server_profile = "unknown",
        realm_id = realm or GetRealmName() or "Unknown",
        latency_ms = clamp(tonumber(ping or 0) or 0, 0, 60000),
        addon_connected = true,
        combat_state = combatState(),
    }
end

local function refresh()
    local _, realm = UnitName("player")
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
    writeCheckpoint(realm, ping)
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

local lifecycle = CreateFrame("Frame")
lifecycle:RegisterEvent("PLAYER_LOGIN")
lifecycle:SetScript("OnEvent", function()
    SentinelDB = SentinelDB or {}
    snapshotSequence = tonumber(SentinelDB.snapshot_sequence or 0) or 0
    snapshotReady = true
    if SentinelDB.overlayHidden then frame:Hide() end
    refresh()
end)

SLASH_SENTINEL1 = "/sentinel"
SlashCmdList.SENTINEL = function(msg)
    msg = (msg or ""):lower()
    SentinelDB = SentinelDB or {}
    if msg == "hide" then
        frame:Hide()
        SentinelDB.overlayHidden = true
    elseif msg == "show" then
        frame:Show()
        SentinelDB.overlayHidden = false
    elseif msg == "lock" then
        locked=true
        paused=true
        refresh()
    else
        print("SENTINEL commands: /sentinel show | hide | lock")
    end
end

refresh()
