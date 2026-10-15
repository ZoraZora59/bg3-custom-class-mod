-- Dedicated save/load boundary: persisted Vars and actual native boosts are
-- independent. This models queued AddBoosts, not native condition evaluation.
local F=Fixture
F.nativeBoostSequence=0;F.nativeBoostQueue={}
local baseAdd,baseRemove=Osi.AddBoosts,Osi.RemoveBoosts
function F.addNativeBoost(id,cause,kind,params,conditionalOnly)
    local actor=F.entities[id]
    F.nativeBoostSequence=F.nativeBoostSequence+1
    local handle='native-boost:'..F.nativeBoostSequence
    F.entities[handle]={BoostInfo={Cause={Cause=cause},Params={Boost=kind,Params=params,Params2=''}},
        _nativeOwner=id,_nativeKind=kind,_nativeParams=params}
    actor.BoostsContainer=actor.BoostsContainer or {Boosts={}}
    if conditionalOnly then
        actor.BoostConditionalState=actor.BoostConditionalState or {States={}}
        table.insert(actor.BoostConditionalState.States,{Boost=handle,ConditionResult=false})
    else
        local group
        for _,row in ipairs(actor.BoostsContainer.Boosts) do if row.Type==kind then group=row end end
        if not group then group={Type=kind,Boosts={}};table.insert(actor.BoostsContainer.Boosts,group) end
        table.insert(group.Boosts,handle)
    end
    if kind=='IncreaseMaxHP' then
        local amount=assert(tonumber(params));actor._maxHp=actor._maxHp+amount;actor._hp=actor._hp+amount
    end
    return handle
end
local function apply(id,boost,cause)
    for statement in boost:gmatch('[^;]+') do
        local body=statement:match('.*%):(.*)') or statement
        local kind,params=body:match('([%w_]+)%((.*)%)')
        assert(kind,'Unsupported fixture boost: '..statement)
        F.addNativeBoost(id,cause,kind,params)
    end
end
function Osi.AddBoosts(id,boost,cause,source)
    baseAdd(id,boost,cause,source)
    -- Existing base fixture separately covers the item Wisdom override.
    if boost=='WeaponAttackRollAbilityOverride(Wisdom)' then return end
    if F.deferNativeBoosts then
        table.insert(F.nativeBoostQueue,{id=id,boost=boost,cause=cause})
    else apply(id,boost,cause) end
end
function F.flushNativeBoosts()
    local queue=F.nativeBoostQueue;F.nativeBoostQueue={}
    for _,row in ipairs(queue) do apply(row.id,row.boost,row.cause) end
end
function Osi.RemoveBoosts(id,boost,unused,cause,source)
    baseRemove(id,boost,unused,cause,source)
    local actor=F.entities[id]
    local removed={}
    local function remove(handle)
        if removed[handle] then return true end
        local info=F.entities[handle] and F.entities[handle].BoostInfo
        if not info or info.Cause.Cause~=cause then return false end
        if info.Params.Boost=='IncreaseMaxHP' then
            local amount=tonumber(info.Params.Params);actor._maxHp=actor._maxHp-amount;actor._hp=math.min(actor._hp,actor._maxHp)
        end
        F.entities[handle]=nil;removed[handle]=true
        return true
    end
    for _,group in pairs(actor.BoostsContainer and actor.BoostsContainer.Boosts or {}) do
        local keep={}
        for _,handle in pairs(group.Boosts) do
            if not remove(handle) then table.insert(keep,handle) end
        end
        group.Boosts=keep
    end
    if actor.BoostConditionalState then
        local keep={}
        for _,row in pairs(actor.BoostConditionalState.States) do
            if not remove(row.Boost) then table.insert(keep,row) end
        end
        actor.BoostConditionalState.States=keep
    end
end
function F.nativeBoostCount(id,cause)
    local count,seen=0,{}
    local function include(handle)
        local info=F.entities[handle] and F.entities[handle].BoostInfo
        if not seen[handle] and info and info.Cause.Cause==cause then count=count+1;seen[handle]=true end
    end
    local actor=F.entities[id]
    for _,group in pairs(actor.BoostsContainer and actor.BoostsContainer.Boosts or {}) do
        for _,handle in pairs(group.Boosts) do include(handle) end
    end
    for _,row in pairs(actor.BoostConditionalState and actor.BoostConditionalState.States or {}) do include(row.Boost) end
    return count
end
