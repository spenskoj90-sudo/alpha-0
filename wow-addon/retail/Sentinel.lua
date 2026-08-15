local ADDON = "SENTINEL"
local db
local overlay
local statusText
local serverText
local securityText
local patchText
local paused = false
local locked = false

local function clamp(v, lo, hi)
    if v < lo then return lo end
    if v > hi then return hi end
    return v
end

local function safeName()
    local name, realm = UnitName("player")
    return name or "Unknown", realm or GetRealmName() or "Unknown"
end

local function latency()
    if GetNetStats then
        local _, _, home, world = GetNetStats()
        return tonumber(world or home or 0) or 0
    end
    return 0
end

local function currentPatch()
    if C_AddOns and C_AddOns.GetAddOnMetadata then
        return C_AddOns.GetAddOnMetadata(ADDON, "Version") or "0.3.0"
    end
    return "0.3.0"
end

local function makeText(parent, size, point, x, y)
    local fs = parent:CreateFontString(nil, "OVERLAY", "GameFontNormal")
    fs:SetFont(fs:GetFont(), size, "OUTLINE")
    fs:SetPoint(point, x, y)
    fs:SetTextColor(0.82, 0.88, 0.92, 1)
    return fs
end

local function makeButton(parent, text, width, callback)
    local b = CreateFrame("Button", nil, parent, "UIPanelButtonTemplate")
    b:SetSize(width, 24)
    b:SetText(text)
    b:SetScript("OnClick", callback)
    return b
end

local function setSecurity(state, reason)
    local r, g, b = 0.2, 0.9, 0.35
    if state == "WARN" then r, g, b = 0.95, 0.72, 0.18 end
    if state == "LOCKED" then r, g, b = 0.95, 0.2, 0.25 end
    securityText:SetText((state == "OK" and "● SECURE") or (state == "WARN" and "● ATTENTION") or "● SESSION LOCKED")
    securityText:SetTextColor(r, g, b, 1)
    if reason then securityText:SetTooltip("ANCHOR") end
end

local function update()
    if not overlay then return end
    local name, realm = safeName()
    local ping = latency()
    local patch = currentPatch()
    statusText:SetText(paused and "SENTINEL  /  PROTECTION PAUSED" or "SENTINEL  /  PROTECTION ACTIVE")
    statusText:SetTextColor(paused and 0.95 or 0.60, paused and 0.70 or 0.85, paused and 0.20 or 0.35, 1)
    serverText:SetText(string.format("REALM  %s\nTYPE   OFFICIAL / PRIVATE: UNKNOWN\nPING   %d ms\nPLAYER %s", realm, clamp(ping, 0, 9999), name))
    patchText:SetText("PATCH PROFILE  " .. patch .. "\nADAPTER  PASSIVE TELEMETRY\nNO GAMEPLAY AUTOMATION")
    if locked then setSecurity("LOCKED") elseif ping > 180 then setSecurity("WARN") else setSecurity("OK") end
end

local function createOverlay()
    overlay = CreateFrame("Frame", "SentinelOverlay", UIParent, "BackdropTemplate")
    overlay:SetSize(330, 150)
    overlay:SetPoint("TOPRIGHT", UIParent, "TOPRIGHT", -24, -90)
    overlay:SetMovable(true)
    overlay:EnableMouse(true)
    overlay:RegisterForDrag("LeftButton")
    overlay:SetScript("OnDragStart", overlay.StartMoving)
    overlay:SetScript("OnDragStop", overlay.StopMovingOrSizing)
    overlay:SetBackdrop({
        bgFile = "Interface\\DialogFrame\\UI-DialogBox-Background",
        edgeFile = "Interface\\Tooltips\\UI-Tooltip-Border",
        edgeSize = 12,
        insets = { left = 4, right = 4, top = 4, bottom = 4 },
    })
    overlay:SetBackdropColor(0.025, 0.04, 0.055, 0.88)
    overlay:SetBackdropBorderColor(0.22, 0.62, 0.76, 0.85)

    statusText = makeText(overlay, 13, "TOPLEFT", 14, -12)
    serverText = makeText(overlay, 10, "TOPLEFT", 14, -36)
    patchText = makeText(overlay, 9, "TOPLEFT", 14, -88)
    securityText = makeText(overlay, 11, "TOPRIGHT", -14, -12)

    local pause = makeButton(overlay, "PAUSE", 60, function()
        if locked then return end
        paused = not paused
        update()
    end)
    pause:SetPoint("BOTTOMLEFT", 12, 10)

    local settings = makeButton(overlay, "SETTINGS", 72, function()
        print("SENTINEL: overlay position is draggable; configuration is managed by the Sentinel control plane.")
    end)
    settings:SetPoint("LEFT", pause, "RIGHT", 6, 0)

    local shot = makeButton(overlay, "SCREENSHOT", 88, function()
        Screenshot()
    end)
    shot:SetPoint("LEFT", settings, "RIGHT", 6, 0)

    local lock = makeButton(overlay, "LOCK", 54, function()
        locked = true
        paused = true
        update()
    end)
    lock:SetPoint("LEFT", shot, "RIGHT", 6, 0)

    overlay:SetScript("OnUpdate", function(self, elapsed)
        self._t = (self._t or 0) + elapsed
        if self._t >= 2 then self._t = 0; update() end
    end)

    update()
end

local frame = CreateFrame("Frame")
frame:RegisterEvent("PLAYER_LOGIN")
frame:RegisterEvent("PLAYER_ENTERING_WORLD")
frame:SetScript("OnEvent", function(_, event)
    if event == "PLAYER_LOGIN" then
        db = SentinelDB or {}
        SentinelDB = db
        if db.overlayHidden then return end
        createOverlay()
    elseif event == "PLAYER_ENTERING_WORLD" then
        update()
    end
end)

SLASH_SENTINEL1 = "/sentinel"
SlashCmdList.SENTINEL = function(msg)
    msg = (msg or ""):lower()
    if msg == "hide" then
        if overlay then overlay:Hide() end
        SentinelDB.overlayHidden = true
    elseif msg == "show" then
        SentinelDB.overlayHidden = false
        if not overlay then createOverlay() else overlay:Show() end
    elseif msg == "lock" then
        locked = true
        paused = true
        update()
    else
        print("SENTINEL commands: /sentinel show | hide | lock")
    end
end
