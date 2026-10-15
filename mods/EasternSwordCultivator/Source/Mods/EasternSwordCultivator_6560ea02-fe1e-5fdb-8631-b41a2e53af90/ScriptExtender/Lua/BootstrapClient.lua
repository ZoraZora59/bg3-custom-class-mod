Ext.Vars.RegisterUserVariable('ESC_State',{Server=true,Client=false,Persistent=true})
Ext.Vars.RegisterUserVariable('ESC_BloodKillReceipts',{Server=true,Client=false,Persistent=true})
-- A native incapacitation state can block hotbar spell execution. This independent
-- client affordance sends an intent; costs, ownership and eligibility stay server-side.
local windows={}
local cooperationWindows={}
Ext.Events.NetMessage:Subscribe(function(evt)
    if evt.Channel~='ESC_CooperationState' then return end
    local ok,data=pcall(Ext.Json.Parse,evt.Payload)
    if not ok or type(data)~='table' or not data.id then return end
    local entry=cooperationWindows[data.id]
    if not data.available then if entry then entry.window.Visible=false end;return end
    if not Ext.IMGUI or not Ext.IMGUI.NewWindow then Ext.Utils.Print('[ESC] ImGui unavailable; cooperation choice cannot be shown.');return end
    if not entry then
        entry={window=Ext.IMGUI.NewWindow('东方剑修 · 同舟破浪###ESC_Cooperation_'..data.id)}
        -- A previous empty dialog can persist a 68x70 ini size. This transient
        -- choice must fit its controls and must not reuse that saved geometry.
        entry.window.NoSavedSettings=true
        entry.window.AlwaysAutoResize=true
        entry.window.NoCollapse=true
        cooperationWindows[data.id]=entry
    end
    -- Children is a native snapshot; RemoveChild is exposed to Lua and destroys
    -- each old control. The C++ RemoveAllChildren method is not a Lua binding.
    for _,child in ipairs(entry.window.Children) do entry.window:RemoveChild(child) end
    entry.token=data.token
    entry.window:AddText('选择这次免费的普通武器攻击或单体伤害戏法。')
    for index,option in ipairs(data.options or {}) do
        local spell=option.spell
        local button=entry.window:AddButton((option.label or '单体伤害戏法')..'###Choice_'..index)
        button.OnClick=function()
            Ext.ClientNet.PostMessageToServer('ESC_CooperationIntent',Ext.Json.Stringify({id=data.id,token=entry.token,spell=spell}))
        end
    end
    local decline=entry.window:AddButton('放弃这次协同')
    decline.OnClick=function()
        Ext.ClientNet.PostMessageToServer('ESC_CooperationIntent',Ext.Json.Stringify({id=data.id,token=entry.token,spell='decline'}))
    end
    entry.window.Visible=true;entry.window.Open=true
    local viewport=Ext.IMGUI.GetViewportSize()
    entry.window:SetSize({0,0},'Always')
    entry.window:SetPos({viewport[1]*.5,viewport[2]*.5},'Always',{.5,.5})
    entry.window:SetCollapsed(false);entry.window:SetFocus()
end)
Ext.Events.NetMessage:Subscribe(function(evt)
    if evt.Channel~='ESC_ControlRescueState' then return end
    local ok,data=pcall(Ext.Json.Parse,evt.Payload)
    if not ok or type(data)~='table' or not data.id then return end
    local entry=windows[data.id]
    if not data.available then
        if entry then entry.window.Visible=false end
        return
    end
    if not Ext.IMGUI or not Ext.IMGUI.NewWindow then
        Ext.Utils.Print('[ESC] Script Extender ImGui is unavailable; controlled self-rescue UI cannot be shown.')
        return
    end
    if not entry then
        local window=Ext.IMGUI.NewWindow('东方剑修 · 受控自救###ESC_Rescue_'..data.id)
        window:AddText('清除束缚、定身、击倒、眩晕、恐惧等剑道已覆盖的控制。')
        local button=window:AddButton('脱困 · 附赠动作 · 4剑元')
        entry={window=window};windows[data.id]=entry
        button.OnClick=function()
            Ext.ClientNet.PostMessageToServer('ESC_ControlRescueIntent',Ext.Json.Stringify({id=data.id,token=entry.token}))
        end
    end
    entry.token=data.token;entry.window.Visible=true;entry.window.Open=true
end)
Ext.Events.SessionLoaded:Subscribe(function()
    for _,entry in pairs(windows) do entry.window.Visible=false end
    for _,entry in pairs(cooperationWindows) do entry.window.Visible=false end
end)
