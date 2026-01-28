function UCB = UCAcquisitionFunction(x, gprMdl, X_train, w_mu, w_sigma,lambda,bounds,...
    Dis_Penalty,Bounds_Penalty,penalty_w1,penalty_w2,Multiply)
    % x: 当前输入点（多维）
    % gprMdl: 高斯过程模型
    % w_mu, w_simga: 权重参数

    % 预测均值和标准差
    [mu, sigma] = predict(gprMdl, x', 'Alpha', 0.05);  % x 为列向量
    
    % 计算采集函数UCB
    ucb = w_sigma * sigma + w_mu * mu;

    penalty=0;
    % 引入距离惩罚，避免过度开发
    if Dis_Penalty        
        distances = vecnorm(X_train(:,1:end)-x',2,2); % 计算与所有已知点的距离
        penalty_dis = exp(-min(distances)/lambda); % 距离惩罚项
        penalty = penalty_w1 * penalty_dis + penalty;        
    end
    % 引入边界惩罚，避免过度在边界探索
    if Bounds_Penalty
        lowerBou = min(x-bounds(:,1));
        upperBou = min(bounds(:,2)-x);
        BoundsDis = min(lowerBou,upperBou);
        penalty_bou = exp(-BoundsDis/lambda);
        penalty = penalty_w2 * penalty_bou + penalty;
    end

    % 计算改进的UCB
    if Multiply
        UCB = ucb.*(1-penalty);
    else
        UCB = ucb - penalty;
    end

end
