%% 混合权重分析函数
function [sigma, improve] = analyze_properties(model, X_test, Y)
    % 计算模型不确定性
    [mu, ysd] = predict(model, X_test);
    sigma = mean(ysd); 
    % sigma_max = max(ysd);
    % 计算改进量（EI期望值）
    % f_best = max(Y);
    f_best = 0;
    improve = mean(max(mu - f_best, 0));
    % improve_max = max(Y);
    % 归一化处理
    sigma = sigma / range(Y);
    improve = improve / range(Y);
end