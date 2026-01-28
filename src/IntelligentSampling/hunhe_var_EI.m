function hunheACQ = hunhe_var_EI(model, x, w_mu, w_sigma) 

    % 获取当前观测值
    [mu, ysd] = predict(model, x);  % 高斯过程模型的预测均值和方差
    var = w_mu * mu + w_sigma * ysd.^2;  % 直接返回预测方差
    % 当前最佳观测值
    bestObservation = max(model.Y);  % 假设最后一列是目标值

    % 计算标准化改进值
    Z = (mu - bestObservation) ./ ysd;  
    ei =  (mu - bestObservation) .* normcdf(Z) +  ysd .* normpdf(Z);  % 期望改进公式

    % 计算模型不确定性
    sigma = mean(ysd); 
    % sigma_max = max(ysd);
    % 计算改进量（EI期望值）
    % f_best = max(model.Y);
    f_best = 0;
    improve = mean(max(mu - f_best, 0));
    % improve_max = max(Y);
    % 归一化处理 
    sigma = sigma / range(model.Y);
    improve = improve / range(model.Y);
    alpha = sigma / (sigma + improve + 1e-6);

    hunheACQ = alpha * var + (1-alpha) * ei;
end