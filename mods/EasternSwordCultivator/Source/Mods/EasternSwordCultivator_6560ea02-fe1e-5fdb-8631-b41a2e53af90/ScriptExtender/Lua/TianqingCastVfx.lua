-- Visual-only cast anticipation and native-contact synchronization.
-- Native spells retain every roll, target, resource payment and damage callback.
local Vfx={}
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
local function effect(value) return type(value)=='string' and value~='' end
function Vfx.New(E,config,schoolPolish)
    local self={};local active={};local generation=0
    local function attached(r) return r and r.lifecycle=='attached-until-casted' end
    local function row(c)
        if not c or not c.alias or c.alias.internal or not c.alias.hand then return nil end
        if c.key=='tianqing_tianfeng' then
            local r=schoolPolish and schoolPolish.enabled and schoolPolish.records
                and schoolPolish.records.tianqing_tianfeng_cast
            return r and attached(r) and r.skill==c.key and r.binding=='cast' and effect(r.effect) and r or nil
        end
        local r=config and config.enabled and config.timing and config.timing[c.key]
        return r and effect(r.prepareEffect) and effect(r.impactEffect) and r or nil
    end
    local function report(message)
        if E.log then E.log('Tianqing cast visual: '..tostring(message)) end
    end
    local function alive(c)
        local ok,result=pcall(function() return E.entity(c.id) and E.alive(c.id) end)
        return ok and result
    end
    local function stop(entry)
        local handles=entry.handles or {};entry.handles={}
        for _,handle in ipairs(handles) do
            -- Official StopLoopEffect(INTEGER64 FxHandle), one input.
            local ok,message=pcall(Osi.StopLoopEffect,handle)
            if not ok then report('stop failed: '..tostring(message)) end
        end
    end
    local function cancelTimer(handle)
        if handle and Ext.Timer.Cancel then pcall(Ext.Timer.Cancel,handle) end
    end
    local function close(c,entry)
        entry.closed=true;stop(entry)
        cancelTimer(entry.startTimer);cancelTimer(entry.endTimer);cancelTimer(entry.timeout)
        entry.startTimer=nil;entry.endTimer=nil;entry.timeout=nil
        active[c]=nil
    end
    local function anchors(c,override)
        local center=point(override or (c.key=='tianqing_bafang' and c.startPosition)
            or c.areaCenter or c.position or c.targetPosition)
        if not center then return nil end
        if c.key~='tianqing_bafang' then return {center} end
        local layout=config.bafang or {};local result={}
        local count=layout.count or 8;local radius=layout.radius or 8
        local search=layout.terrainSearchRadius or 1
        -- Eight bounded AI-grid queries, once per cast; never per victim.
        for i=0,count-1 do
            local angle=math.rad((layout.angleOffset or 22.5)+i*360/count)
            local p={center[1]+radius*math.cos(angle),center[2],center[3]+radius*math.sin(angle)}
            local ok,x,y,z=pcall(Osi.FindValidPosition,p[1],p[2],p[3],search,NULL,0)
            local found=point({x,y,z})
            if ok and found and (x-p[1])^2+(z-p[3])^2<=search^2 and math.abs(y-p[2])<=6 then p=found end
            result[#result+1]=p
        end
        return result
    end
    local function entryFor(c)
        if not row(c) then return nil end
        local entry=c.tianqingCastVisual
        if not entry then
            entry={handles={},generation=generation};c.tianqingCastVisual=entry;active[c]=entry
        end
        return entry
    end
    local function start(c,entry)
        if entry.closed or entry.started or entry.generation~=generation or c.failed or c.invalid or not alive(c) then return end
        if attached(row(c)) then
            if c.finished then return end
            entry.started=true
            -- One root-attached handle for the whole Rush, including zero
            -- movement. Native damage callbacks must not end this loop.
            local ok,handle=pcall(Osi.PlayLoopEffect,c.id,row(c).effect,'Dummy_Root',1)
            if ok and handle and handle~=0 then entry.handles[#entry.handles+1]=handle
            else report('attached cast effect did not return a handle') end
            return
        end
        local positions=anchors(c)
        if not positions then return end
        entry.started=true;entry.anchors=positions
        for _,p in ipairs(positions) do
            -- Official query: effect,X,Y,Z,scale -> INTEGER64 FxHandle.
            -- The authored LeadIn falls once; Loop only holds the sword above
            -- the ground. StopLoopEffect transitions to its short LeadOut.
            local ok,handle=pcall(Osi.PlayLoopEffectAtPosition,row(c).prepareEffect,p[1],p[2],p[3],1)
            if ok and handle and handle~=0 then entry.handles[#entry.handles+1]=handle
            else report('prepare effect did not return a handle') end
        end
    end
    function self.Enabled(c) return row(c)~=nil end
    function self.Begin(c)
        if c and c.finished and attached(row(c)) then return end
        local entry=entryFor(c)
        if not entry or entry.closed or entry.started or entry.startTimer or c.failed or c.invalid then return end
        -- Collect the same callback batch before choosing an AOE center. An
        -- explicit UsingSpellAtPosition wins over per-victim OnTarget events.
        local current=generation
        entry.startTimer=Ext.Timer.WaitFor(1,function()
            entry.startTimer=nil
            if generation==current and not entry.closed then start(c,entry) end
        end)
        if not entry.timeout then
            -- Visual cleanup only: never cancel a native spell or replay damage.
            entry.timeout=Ext.Timer.WaitFor(8000,function()
                if generation==current and not entry.closed then close(c,entry) end
            end)
        end
    end
    function self.Impact(c,actualPosition)
        if attached(row(c)) then return false end
        local entry=entryFor(c)
        if not entry or entry.closed or entry.impacted or entry.generation~=generation
            or c.failed or c.invalid or not alive(c) then return false end
        -- A native landing uses its actual CreateExplosion position. Other
        -- skills retain the original whole-cast anchor even if a victim moves.
        local positions=actualPosition and anchors(c,actualPosition) or entry.anchors or anchors(c)
        if not positions then return false end
        entry.impacted=true;close(c,entry)
        for _,p in ipairs(positions) do
            local ok,message=pcall(Osi.PlayEffectAtPosition,row(c).impactEffect,p[1],p[2],p[3],1)
            if not ok then report('impact failed: '..tostring(message)) end
        end
        return true
    end
    function self.Finish(c)
        local entry=entryFor(c)
        if not entry or entry.closed or entry.endTimer then return end
        -- Jump completion and CreateExplosion can be distinct callbacks. Only
        -- the real landing may resolve Tianjian's visual, including empty areas.
        if c.key=='tianqing_tianjian' then return end
        local current=generation
        entry.endTimer=Ext.Timer.WaitFor(1,function()
            entry.endTimer=nil
            if generation==current and not entry.closed then close(c,entry) end
        end)
    end
    function self.Cancel(c)
        local entry=entryFor(c)
        if entry and not entry.closed then close(c,entry) end
    end
    function self.CancelOwner(id)
        local pending={}
        for c in pairs(active) do
            local ok,same=pcall(E.sameEntity,c.id,id)
            if ok and same then pending[#pending+1]=c end
        end
        for _,c in ipairs(pending) do self.Cancel(c) end
    end
    function self.Reset()
        local pending={};for c in pairs(active) do pending[#pending+1]=c end
        for _,c in ipairs(pending) do self.Cancel(c) end
        generation=generation+1
    end
    return self
end
return Vfx
