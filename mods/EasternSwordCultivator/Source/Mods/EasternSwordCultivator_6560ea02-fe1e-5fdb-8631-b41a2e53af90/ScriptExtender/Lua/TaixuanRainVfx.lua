-- Pure one-shot world VFX. No damage, native casts, costs, clocks or saved state.
local Rain={}
local NULL='NULL_00000000-0000-0000-0000-000000000000'
local function point(value)
    if not value then return nil end
    local result={}
    for i=1,3 do
        local n=value[i]
        if type(n)~='number' or n~=n or math.abs(n)==math.huge then return nil end
        result[i]=n
    end
    return result
end
local function safe(fn,...)
    local ok,result=pcall(fn,...)
    return ok and result or nil
end
local function relevant(c)
    return c and (c.key=='taixuan_jiuxiao' or c.key=='internal_taiqing_pulse')
end
function Rain.New(E,config)
    local self={}
    local function uuid(id) return safe(function() return E.uuid(E.entity(id)) end) end
    local function ground(p)
        -- AI-grid search, not terrain raycasting. Bound correction prevents
        -- nearby floors/occupied grid cells from collapsing the focus triangle.
        local ok,x,y,z=pcall(Osi.FindValidPosition,p[1],p[2],p[3],.15,NULL,0)
        local found=point({x,y,z})
        if ok and found and (x-p[1])^2+(z-p[3])^2<=.15^2+.00000001 and math.abs(y-p[2])<=.6 then
            return found
        end
        return p
    end
    local function play(role,p)
        local row=config and config.enabled and config.records and config.records[role]
        if not row or type(row.effect)~='string' or row.effect=='' or not point(p) then return false end
        p=ground(p)
        -- Installed story_header.div: EFFECTRESOURCE, X, Y, Z, Scale.
        local ok=pcall(Osi.PlayEffectAtPosition,row.effect,p[1],p[2],p[3],1)
        return ok
    end
    local function render(c,id,p)
        c.taixuanRainRendered=c.taixuanRainRendered or {}
        if c.taixuanRainRendered[id] then return false end
        local meta=c.meta or {};local offset={0,0}
        if c.key=='internal_taiqing_pulse' and meta.rainFocused then
            offset=({{-.4,-.23},{.4,-.23},{0,.46}})[meta.rainIndex or 1] or offset
        end
        local role=c.key=='taixuan_jiuxiao' and 'jiuxiao' or 'taiqing'
        c.taixuanRainRendered[id]=true
        return play(role,{p[1]+offset[1],p[2],p[3]+offset[2]})
    end
    function self.Capture(c,target)
        if not relevant(c) or c.taixuanRainCancelled or not target then return end
        local id=uuid(target)
        local p=safe(function() return point(E.position(target)) end)
        if not id or not p then return end
        -- Both native Taiqing target delivery and area damage victims may
        -- arrive after CastedSpell. Add their one actual attempt without
        -- replaying already rendered targets or guessing a target at Finish.
        if c.taixuanRainPlayed then
            if not c.failed and not c.invalid
                and safe(function() return E.entity(c.id) and E.alive(c.id) end) then render(c,id,p) end
            return
        end
        c.taixuanRainTargets=c.taixuanRainTargets or {}
        if not c.taixuanRainTargets[id] then
            c.taixuanRainTargets[id]={id=id,point=p}
        end
    end
    function self.Finish(c)
        if not relevant(c) or c.failed or c.invalid or c.taixuanRainCancelled or c.taixuanRainPlayed then return 0 end
        c.taixuanRainPlayed=true
        c.taixuanRainRendered={}
        local count=0
        if not safe(function() return E.entity(c.id) and E.alive(c.id) end) then self.Cancel(c);return count end
        if c.key=='taixuan_jiuxiao' then
            local center=point(c.areaCenter or c.position or c.targetPosition)
            if center then
                -- Three sparse annuli remain strictly inside the existing 6m area.
                for _,ring in ipairs({{2,4},{4,6},{5.6,8}}) do
                    for i=0,ring[2]-1 do
                        local angle=math.rad(22.5)+i*2*math.pi/ring[2]
                        if play('jiuxiao_background',{center[1]+ring[1]*math.cos(angle),center[2],center[3]+ring[1]*math.sin(angle)}) then count=count+1 end
                    end
                end
            end
        end
        -- Successful native casts include misses. Every attempted Taiqing roll
        -- gets one sword; native HitEffect remains the actual-hit glint only.
        local ids={}
        for id in pairs(c.taixuanRainTargets or {}) do ids[#ids+1]=id end
        table.sort(ids)
        for _,id in ipairs(ids) do
            local row=c.taixuanRainTargets[id]
            -- Dead but present targets can show the killing strike. Missing
            -- targets are discarded; only copied numbers cross event boundaries.
            if uuid(row.id) then
                if render(c,id,row.point) then count=count+1 end
            end
        end
        c.taixuanRainTargets=nil
        return count
    end
    function self.Cancel(c)
        if relevant(c) then c.taixuanRainTargets=nil;c.taixuanRainRendered=nil;c.taixuanRainCancelled=true end
    end
    function self.CancelOwner(casts,id)
        for _,c in pairs(casts) do
            if relevant(c) and safe(function() return E.sameEntity(c.id,id) end) then self.Cancel(c) end
        end
    end
    return self
end
return Rain
