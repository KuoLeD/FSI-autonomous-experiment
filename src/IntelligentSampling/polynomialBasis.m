function phi = polynomialBasis(x,order)

phi =zeros(size(x,1),(order+1)*size(x,2));
for j=1:size(x,2)
    for i=1:order
        phi(:,i+(j-1)*(order+1))=x(:,j).^i; % 生成多项式基
    end
end
end