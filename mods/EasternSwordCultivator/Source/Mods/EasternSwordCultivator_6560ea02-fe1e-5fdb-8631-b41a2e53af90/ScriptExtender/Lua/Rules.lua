-- Pure confirmed design rules. No engine calls: the same code runs in regression tests.
local R = {}
R.capacities = {0,6,10,14,18,24,26,28,30,40,44,50}
R.hpMultipliers = {taixuan=1.8,tianqing=2.5,xueyan=1.6,xingge=1.1}

function R.clamp(value, low, high) return math.max(low, math.min(value, high)) end
function R.capacity(level) return R.capacities[R.clamp(level,1,12)] end
function R.modifier(ability) return math.floor((ability - 10)/2) end
function R.hitpoints(level, constitution, branch)
    local hp = 10 + constitution + (level-1)*(6+constitution)
    return math.ceil(hp * (level >= 3 and (R.hpMultipliers[branch] or 1) or 1))
end
function R.opportunities(level, branch)
    if level < 5 then return 1 end
    if branch == 'xingge' then return 2 end
    return level >= 10 and 4 or 3
end
function R.attackBonus(level, branch)
    local value = level < 3 and 1 or ({taixuan=6,tianqing=4,xueyan=3,xingge=1})[branch] or 1
    return value + (level >= 11 and 1 or 0)
end
function R.recover(current, capacity, amount)
    local nextValue = R.clamp(current + math.ceil(amount), 0, capacity)
    return nextValue, nextValue - current
end
function R.breath(level, branch, active, inCombat)
    if active and not inCombat then return R.capacity(level) end
    local ratio
    if active then
        ratio = branch == 'tianqing' and (level >= 11 and .70 or .60)
            or branch == 'taixuan' and level >= 11 and .50 or .40
    else
        ratio = branch == 'taixuan' and (level >= 11 and .25 or .20) or 0
    end
    return math.ceil(R.capacity(level)*ratio)
end
function R.healing(level, branch)
    if branch == 'taixuan' or branch == 'xueyan' then return .40,6 end
    if branch == 'tianqing' then
        return level < 4 and .35 or level >= 11 and .80 or .75, level < 4 and 5 or 10
    end
    return level < 4 and .15 or .30, level < 4 and 4 or 6
end
function R.frenzyGained(lostHp, maxHp, deliberate)
    if deliberate or lostHp <= 0 then return 0 end
    return 1 + (lostHp >= maxHp*.10 and 2 or 0)
end
function R.spendFrenzy(held, requested)
    local spent = R.clamp(math.floor(requested),0,held)
    return {held=held, spent=spent, remaining=held-spent,
            attack=math.floor(held/2), bonus=held*.05+spent*.10}
end
function R.bloodCost(hp, maxHp, held)
    local cost = math.ceil(maxHp*.10)
    if hp <= cost then return nil,held end
    return hp-cost, R.clamp(held+4,0,15)
end
function R.siphon(level, finalDamage, maxHp, shield)
    if finalDamage <= 0 then return 0,0,shield end
    return math.ceil(finalDamage*(level >= 11 and .25 or .20)), level >= 11 and 2 or 1,
        math.min(math.ceil(maxHp*.20),shield+math.ceil(finalDamage*.10))
end
function R.killReward(level, maxHp)
    return math.ceil(maxHp*.10),level >= 11 and 4 or 3,2
end
function R.baseReduction(level, branch, frenzy)
    if level < 3 then return 0 end
    return (({taixuan=level>=11 and .25 or .20,tianqing=level>=11 and .40 or .35,
        xueyan=(level>=11 and .25 or .20)+(frenzy or 0)*.02,xingge=0})[branch] or 0)
end
function R.reduce(damage, base, other)
    local result = damage*(1-base)
    for _, reduction in ipairs(other or {}) do result = result*(1-reduction) end
    return math.floor(math.max(0,result)+1e-9)
end
function R.share(damage, sharePercent, receiverReduction, other)
    local transfer = math.floor(damage*sharePercent)
    return damage-transfer,R.reduce(transfer,receiverReduction,other),transfer
end
function R.damageMultiplier(options)
    local bonus = (options.held or 0)*.05+(options.spent or 0)*.10
    if options.weakpoint then bonus=bonus+.20 end
    if options.domain then bonus=bonus+.20 end
    if options.followup then bonus=bonus+.15 end
    if options.charge then bonus=bonus+.30 end
    if options.descent then bonus=bonus+.40 end
    if options.team then bonus=bonus+.30 end
    if options.regular and options.level>=10 then bonus=bonus+.15 end
    return 1+bonus
end
function R.falloff(baseDamage, immunity)
    local result, index = {},0
    for _, immune in ipairs(immunity) do
        if immune then result[#result+1]=0 else
            result[#result+1]=math.floor(baseDamage*(.5^index)); index=index+1
        end
    end
    return result
end
function R.shieldAbsorb(damage, shield)
    local absorbed = math.min(damage,shield)
    return damage-absorbed,shield-absorbed
end
function R.guard(existing, requested, turn)
    -- A weaker guard neither replaces nor refreshes the stronger one.
    if existing and existing.expires > turn and existing.rank > requested.rank then return existing,false end
    return {rank=requested.rank,ac=requested.ac,reduction=requested.reduction,
        dice=requested.dice,attack=requested.attack,expires=turn+2},true
end
function R.applyDuration(existing, turn, duration)
    local state = existing or {used={}}
    state.expires = turn+duration
    return state
end
function R.tickDuration(state, turn)
    -- Expiration precedes periodic damage: four-round domain hits four times total.
    return state and turn < state.expires
end
function R.followup(state, teammate)
    if state.used[teammate] then return false end
    state.used[teammate]=true
    return true
end
function R.recastFollowup(turn)
    -- This is the one explicitly allowed exception to preserving reward eligibility.
    return {expires=turn+3,used={}}
end
function R.cooperation(level) return level>=11 and 3 or 2 end
function R.normalRecovery(level) return level>=11 and 2 or 1 end
function R.chooseShare(protectors)
    local best
    for _, protector in ipairs(protectors) do
        if not best or protector.percent>best.percent
            or protector.percent==best.percent and protector.sequence>best.sequence then best=protector end
    end
    return best
end
function R.once(cache, key)
    if cache[key] then return false end
    cache[key]=true
    return true
end
function R.within(position, center, distance)
    return (position[1]-center[1])^2+(position[2]-center[2])^2+(position[3]-center[3])^2<=distance^2
end
function R.inLine(position, start, finish, width)
    local dx,dz=finish[1]-start[1],finish[3]-start[3]
    local lengthSquared=dx*dx+dz*dz
    if lengthSquared<=0 then return false end
    local t=((position[1]-start[1])*dx+(position[3]-start[3])*dz)/lengthSquared
    if t<0 or t>1 then return false end
    local x,z=start[1]+t*dx,start[3]+t*dz
    return (position[1]-x)^2+(position[3]-z)^2<=(width/2)^2,t
end
function R.canFly(enemies, position)
    for _, enemy in ipairs(enemies) do if R.within(enemy,position,3) then return false end end
    return true
end
return R
