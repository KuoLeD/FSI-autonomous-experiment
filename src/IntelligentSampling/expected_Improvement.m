function ei = expected_Improvement(model, x)

    % 获取当前观测值
    [mu, sigma] = predict(model, x);  % 高斯过程模型的预测均值和方差
    
    % 当前最佳观测值
    bestObservation = max(model.Y);  % 假设最后一列是目标值

    % 计算标准化改进值
    Z = (mu - bestObservation) ./ sigma;  
    ei =  (mu - bestObservation) .* normcdf(Z) +  sigma .* normpdf(Z);  % 期望改进公式
end